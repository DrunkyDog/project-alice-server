import time
import asyncio
import logging
import statistics
import base64
from typing import Dict
from tabulate import tabulate
from core.utils.vllm import create_instance
from config.settings import load_config

# Set global logging level to WARNING to suppress INFO logs
logging.basicConfig(level=logging.WARNING)

description = "Vision Recognition Model Performance Test"


class AsyncVisionPerformanceTester:
    def __init__(self):
        self.config = load_config()

        self.test_images = [
            "../../docs/images/demo1.png",
            "../../docs/images/demo2.png",
        ]
        self.test_questions = [
            "What is in this image?",
            "Please describe this image in detail",
        ]

        # 加载测试图片
        self.results = {"vllm": {}}

    async def _test_vllm(self, vllm_name: str, config: Dict) -> Dict:
        """Asynchronously test a single vision model performance"""
        try:
            # Check API key configuration
            if "api_key" in config and any(
                x in config["api_key"] for x in ["your", "placeholder", "sk-xxx"]
            ):
                print(f"⏭️  VLLM {vllm_name} api_key not configured, skipped")
                return {"name": vllm_name, "type": "vllm", "errors": 1}

            # Get actual type (compatible with old configuration)
            module_type = config.get("type", vllm_name)
            vllm = create_instance(module_type, config)

            print(f"🖼️ Testing VLLM: {vllm_name}")

            # Create all test tasks
            test_tasks = []
            for question in self.test_questions:
                for image in self.test_images:
                    test_tasks.append(
                        self._test_single_vision(vllm_name, vllm, question, image)
                    )

            # Run all tests concurrently
            test_results = await asyncio.gather(*test_tasks)

            # Process results
            valid_results = [r for r in test_results if r is not None]
            if not valid_results:
                print(f"⚠️  {vllm_name} No valid data, possible configuration error")
                return {"name": vllm_name, "type": "vllm", "errors": 1}

            response_times = [r["response_time"] for r in valid_results]

            # Filter outliers
            mean = statistics.mean(response_times)
            stdev = statistics.stdev(response_times) if len(response_times) > 1 else 0
            filtered_times = [t for t in response_times if t <= mean + 3 * stdev]

            if len(filtered_times) < len(test_tasks) * 0.5:
                print(f"⚠️  {vllm_name} Insufficient valid data, network may be unstable")
                return {"name": vllm_name, "type": "vllm", "errors": 1}

            return {
                "name": vllm_name,
                "type": "vllm",
                "avg_response": sum(response_times) / len(response_times),
                "std_response": (
                    statistics.stdev(response_times) if len(response_times) > 1 else 0
                ),
                "errors": 0,
            }

        except Exception as e:
            print(f"⚠️ VLLM {vllm_name} test failed: {str(e)}")
            return {"name": vllm_name, "type": "vllm", "errors": 1}

    async def _test_single_vision(
        self, vllm_name: str, vllm, question: str, image: str
    ) -> Dict:
        """Test performance for a single vision question"""
        try:
            print(f"📝 {vllm_name} Start testing: {question[:20]}...")
            start_time = time.time()

            # Read image and convert to Base64
            with open(image, "rb") as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")

            # Get response directly
            response = vllm.response(question, image_base64)
            response_time = time.time() - start_time
            print(f"✓ {vllm_name} Response completed: {response_time:.3f}s")

            return {
                "name": vllm_name,
                "type": "vllm",
                "response_time": response_time,
            }
        except Exception as e:
            print(f"⚠️ {vllm_name} test failed: {str(e)}")
            return None

    def _print_results(self):
        """Print test results"""
        vllm_table = []
        for name, data in self.results["vllm"].items():
            if data["errors"] == 0:
                stability = data["std_response"] / data["avg_response"]
                vllm_table.append(
                    [
                        name,
                        f"{data['avg_response']:.3f}s",
                        f"{stability:.3f}",
                    ]
                )

        if vllm_table:
            print("\nVision Model Performance Ranking:\n")
            print(
                tabulate(
                    vllm_table,
                    headers=["Model", "Response Time", "Stability"],
                    tablefmt="github",
                    colalign=("left", "right", "right"),
                    disable_numparse=True,
                )
            )
        else:
            print("\n⚠️ No available vision models for testing.")

    async def run(self):
        """Run full asynchronous test"""
        print("🔍 Searching for available vision models...")

        if not self.test_images:
            print(f"\n⚠️  {self.image_root} No image files found in the path; unable to run tests")
            return

        # Create all test tasks
        all_tasks = []

        # VLLM test tasks
        if self.config.get("VLLM") is not None:
            for vllm_name, config in self.config.get("VLLM", {}).items():
                if "api_key" in config and any(
                    x in config["api_key"] for x in ["your", "placeholder", "sk-xxx"]
                ):
                    print(f"⏭️  VLLM {vllm_name} api_key not configured, skipped")
                    continue
                print(f"🖼️ 添加VLLM test tasks: {vllm_name}")
                all_tasks.append(self._test_vllm(vllm_name, config))

        print(f"\n✅ Found {len(all_tasks)} available vision models")
        print(f"✅ 使用 {len(self.test_images)} test images")
        print(f"✅ 使用 {len(self.test_questions)} test questions")
        print("\n⏳ Start concurrent testing of all models...\n")

        # Run all tests concurrently任务
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Process results
        for result in all_results:
            if isinstance(result, dict) and result["errors"] == 0:
                self.results["vllm"][result["name"]] = result

        # 打印结果
        print("\n📊 Generating test report...")
        self._print_results()


async def main():
    tester = AsyncVisionPerformanceTester()
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
