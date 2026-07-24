import time
import asyncio
from collections import deque
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class AudioRateController:
    """
    Audio rate controller - precisely control audio sending based on 60ms frame duration
    Solves the problem of accumulated time errors under high concurrency
    """

    def __init__(self, frame_duration=60):
        """
        Args:
            frame_duration: Single audio frame duration (milliseconds), default 60ms
        """
        self.frame_duration = frame_duration
        self.queue = deque()
        self.play_position = 0  # Virtual play position (milliseconds)
        self.start_timestamp = None  # Start timestamp (read-only, do not modify)
        self.pending_send_task = None
        self.logger = logger
        self.queue_empty_event = asyncio.Event()  # Queue empty event
        self.queue_empty_event.set()  # Initial state is empty
        self.queue_has_data_event = asyncio.Event()  # Queue has data event
        self._last_queue_empty_time = 0  # Last time queue became empty (seconds)

    def reset(self):
        """Reset controller state"""
        if self.pending_send_task and not self.pending_send_task.done():
            self.pending_send_task.cancel()
            # After cancelling task, it will be cleaned up in the next event loop without blocking wait

        self.queue.clear()
        self.play_position = 0
        self.start_timestamp = None  # Set by the first audio packet
        self._last_queue_empty_time = 0  # Reset time
        # Related event handling
        self.queue_empty_event.set()
        self.queue_has_data_event.clear()

    def add_audio(self, opus_packet):
        """Add audio packet to queue"""
        # If queue was previously empty, need to adjust timestamp to keep playback time continuous
        # This prevents newly added audio from playing early during tool call waiting periods
        # If interval is very short (<1 frame), it indicates normal streaming and does not need reset
        if len(self.queue) == 0 and self.play_position > 0:
            elapsed_since_empty = (time.monotonic() - self._last_queue_empty_time) * 1000
            # Only when interval exceeds 1 frame duration, it is considered a true "pause and resume"
            if elapsed_since_empty >= self.frame_duration:
                self.start_timestamp = time.monotonic() - (self.play_position / 1000)
                self.logger.bind(tag=TAG).debug(
                    f"Queue recovered from empty, resetting timestamp, current play position: {self.play_position}ms, interval: {elapsed_since_empty:.0f}ms"
                )

        self.queue.append(("audio", opus_packet))
        # Related event handling
        self.queue_empty_event.clear()
        self.queue_has_data_event.set()

    def add_message(self, message_callback):
        """
        Add message to queue (send immediately, does not consume playback time)

        Args:
            message_callback: Message sending callback function async def()
        """
        if len(self.queue) == 0 and self.play_position > 0:
            elapsed_since_empty = (time.monotonic() - self._last_queue_empty_time) * 1000
            if elapsed_since_empty >= self.frame_duration:
                self.start_timestamp = time.monotonic() - (self.play_position / 1000)
                self.logger.bind(tag=TAG).debug(
                    f"Queue recovered from empty, resetting timestamp, current play position: {self.play_position}ms, interval: {elapsed_since_empty:.0f}ms"
                )

        self.queue.append(("message", message_callback))
        # Related event handling
        self.queue_empty_event.clear()
        self.queue_has_data_event.set()

    def _get_elapsed_ms(self):
        """Get elapsed time (milliseconds)"""
        if self.start_timestamp is None:
            return 0
        return (time.monotonic() - self.start_timestamp) * 1000

    async def check_queue(self, send_audio_callback):
        """
        Check queue and send audio/message on schedule

        Args:
            send_audio_callback: Callback function to send audio async def(opus_packet)
        """
        while self.queue:
            item = self.queue[0]
            item_type = item[0]

            if item_type == "message":
                # Message type: send immediately, does not consume playback time
                _, message_callback = item
                self.queue.popleft()
                try:
                    await message_callback()
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Failed to send message: {e}")
                    raise

            elif item_type == "audio":
                if self.start_timestamp is None:
                    self.start_timestamp = time.monotonic()

                _, opus_packet = item

                # Loop wait until time arrives
                while True:
                    # Calculate time difference
                    elapsed_ms = self._get_elapsed_ms()
                    output_ms = self.play_position

                    if elapsed_ms < output_ms:
                        # Not time to send yet, calculate wait time
                        wait_ms = output_ms - elapsed_ms

                        # Continue checking after wait (allows interruption)
                        try:
                            await asyncio.sleep(wait_ms / 1000)
                        except asyncio.CancelledError:
                            self.logger.bind(tag=TAG).debug("Audio sending task was cancelled")
                            raise
                        # Re-check time after wait ends (loops back to while True)
                    else:
                        # Time is up, break out of wait loop
                        break

                # Time is up, remove from queue and send
                self.queue.popleft()
                self.play_position += self.frame_duration
                try:
                    await send_audio_callback(opus_packet)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Failed to send audio: {e}")
                    raise

        # Clear event after queue is processed
        self.queue_empty_event.set()
        self.queue_has_data_event.clear()
        self._last_queue_empty_time = time.monotonic()  # Record queue empty time

    def start_sending(self, send_audio_callback):
        """
        Start async sending task

        Args:
            send_audio_callback: Callback function to send audio

        Returns:
            asyncio.Task: Sending task
        """

        async def _send_loop():
            try:
                while True:
                    # Wait for queue data event without polling to avoid CPU usage
                    await self.queue_has_data_event.wait()

                    await self.check_queue(send_audio_callback)
            except asyncio.CancelledError:
                self.logger.bind(tag=TAG).debug("Audio sending loop stopped")
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"Audio sending loop exception: {e}")

        self.pending_send_task = asyncio.create_task(_send_loop())
        return self.pending_send_task

    def stop_sending(self):
        """Stop sending task"""
        if self.pending_send_task and not self.pending_send_task.done():
            self.pending_send_task.cancel()
            self.logger.bind(tag=TAG).debug("Cancelled audio sending task")
