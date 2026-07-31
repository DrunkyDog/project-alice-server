// Feature Configuration Tool
import Api from "@/apis/api";
import store from "@/store";

class FeatureManager {
    constructor() {
        this.defaultFeatures = {
            voiceprintRecognition: {
                name: 'feature.voiceprintRecognition.name',
                enabled: false,
                description: 'feature.voiceprintRecognition.description'
            },
            voiceClone: {
                name: 'feature.voiceClone.name',
                enabled: false,
                description: 'feature.voiceClone.description'
            },
            knowledgeBase: {
                name: 'feature.knowledgeBase.name',
                enabled: false,
                description: 'feature.knowledgeBase.description'
            },
            mcpAccessPoint: {
                name: 'feature.mcpAccessPoint.name',
                enabled: false,
                description: 'feature.mcpAccessPoint.description'
            },
            vad: {
                name: 'feature.vad.name',
                enabled: false,
                description: 'feature.vad.description'
            },
            asr: {
                name: 'feature.asr.name',
                enabled: false,
                description: 'feature.asr.description'
            },
            addressBook: {
                name: 'feature.addressBook.name',
                enabled: false,
                description: 'feature.addressBook.description'
            }
        };
        this.currentFeatures = { ...this.defaultFeatures }; // Current configuration in memory
        this.initialized = false;
        this.initPromise = null;
    }

    /**
     * Wait for initialization to complete
     */
    async waitForInitialization() {
        if (!this.initPromise) {
            this.initPromise = this.init();
        }
        await this.initPromise;
        return this.initialized;
    }

    /**
     * Initialize feature configuration
     */
    async init() {
        try {
            // Get configuration from pub-config interface
            const config = await this.getConfigFromPubConfig();
            if (config) {
                this.currentFeatures = { ...config }; // Save to memory
                this.initialized = true;
                return;
            }
        } catch (error) {
            console.warn('Failed to get configuration from pub-config interface:', error);
        }

        // pub-config interface failed, using default configuration
        this.currentFeatures = { ...this.defaultFeatures }; // Save default configuration to memory
        this.initialized = true;
    }

    /**
     * Update config cache
     */
    updateConfigCache(config) {
        store.commit('setPubConfig', config);
        localStorage.setItem('pubConfig', JSON.stringify(config));
    }

    /**
     * Get configuration from pub-config interface
     */
    async getConfigFromPubConfig() {
        return new Promise((resolve) => {
            // Directly call the pub-config interface to get configuration
            Api.user.getPubConfig((result) => {
                // Check the structure of the returned result
                if (result && result.status === 200) {
                    // Check if the data field exists
                    if (result.data) {
                        const configCache = result.data.data || {};
                        // Check if the code field exists, if so, judge by code
                        if (result.data.code !== undefined) {
                            if (result.data.code === 0 && result.data.data && result.data.data.systemWebMenu) {
                                try {
                                    let config;
                                    if (typeof result.data.data.systemWebMenu === 'string') {
                                        // If it is a string, need to parse JSON
                                        config = JSON.parse(result.data.data.systemWebMenu);
                                    } else {
                                        // If it is already an object, use it directly
                                        config = result.data.data.systemWebMenu;
                                    }

                                    // Check if the configuration contains the features object
                                    if (config && config.features) {
                                        // Ensure knowledgeBase feature exists and is configured correctly
                                        if (!config.features.knowledgeBase) {
                                            console.warn('Missing knowledgeBase feature in configuration, merging default configuration');
                                            config.features = { ...this.defaultFeatures, ...config.features };
                                        }
                                        resolve(config.features);
                                    } else {
                                        console.warn('Missing features object in configuration, using default configuration');
                                        resolve(this.defaultFeatures);
                                    }
                                    configCache.systemWebMenu = config;
                                } catch (error) {
                                    console.warn('Failed to process systemWebMenu configuration:', error);
                                    resolve(null);
                                }
                            } else {
                                console.warn('Interface returned non-zero code or missing necessary data, using default configuration');
                                resolve(null);
                            }
                        } else {
                            // If there is no code field, directly check systemWebMenu
                            if (result.data && result.data.systemWebMenu) {
                                try {
                                    let config;
                                    if (typeof result.data.systemWebMenu === 'string') {
                                        // If it is a string, need to parse JSON
                                        config = JSON.parse(result.data.systemWebMenu);
                                    } else {
                                        // If it is already an object, use it directly
                                        config = result.data.systemWebMenu;
                                    }

                                    // Check if the configuration contains the features object
                                    if (config && config.features) {
                                        // Ensure knowledgeBase feature exists and is configured correctly
                                        if (!config.features.knowledgeBase) {
                                            console.warn('Missing knowledgeBase feature in configuration, merging default configuration');
                                            config.features = { ...this.defaultFeatures, ...config.features };
                                        }
                                        resolve(config.features);
                                    } else {
                                        console.warn('Missing features object in configuration, using default configuration');
                                        resolve(this.defaultFeatures);
                                    }
                                    configCache.systemWebMenu = config;
                                } catch (error) {
                                    console.warn('Failed to process systemWebMenu configuration:', error);
                                    resolve(null);
                                }
                            } else {
                                console.warn('Interface returned missing systemWebMenu data, using default configuration');
                                resolve(null);
                            }
                        }
                        this.updateConfigCache(configCache)
                    } else {
                        console.warn('Interface returned data missing data field, using default configuration');
                        resolve(null);
                    }
                } else {
                    console.warn('pub-config interface call failed, using default configuration');
                    resolve(null);
                }
            });
        });
    }

    /**
     * Get current configuration
     */
    getCurrentConfig() {
        // Return current configuration in memory
        return this.currentFeatures;
    }

    /**
     * Save configuration to backend API
     */
    async saveConfig(config) {
        try {
            // Update configuration in memory
            this.currentFeatures = { ...config };

            // Asynchronously save to backend API
            this.saveConfigToAPI(config).catch(error => {
                console.warn('Failed to save configuration to API:', error);
            }).finally(() => {
                this.init()
            });

            // Trigger configuration change event
            window.dispatchEvent(new CustomEvent('featureConfigChanged', {
                detail: config
            }));
        } catch (error) {
            console.error('Failed to save feature configuration:', error);
        }
    }

    /**
     * Save configuration to backend API
     */
    async saveConfigToAPI(config) {
        return new Promise((resolve) => {
            // Directly use the known ID (600) to update parameters
            Api.admin.updateParam(
                {
                    id: 600,
                    paramCode: 'system-web.menu',
                    paramValue: JSON.stringify({
                        features: config,
                        groups: {
                            featureManagement: ["voiceprintRecognition", "voiceClone", "knowledgeBase", "mcpAccessPoint", "addressBook"],
                            voiceManagement: ["vad", "asr"]
                        }
                    }),
                    valueType: 'json',
                    remark: 'System feature menu configuration'
                },
                (updateResult) => {
                    if (updateResult.code === 0) {
                        resolve();
                    } else {
                        // If the update fails, it may be due to a non-existent parameter or other error, log it but do not block saving to localStorage
                        console.warn('Failed to update parameters:', updateResult.msg);
                        resolve(); // Do not block saving to localStorage
                    }
                },
                (error) => {
                    console.warn('Failed to update parameters:', error);
                    resolve(); // Do not block saving to localStorage
                }
            );
        });
    }
    

    /**
     * Get all feature configurations
     */
    getAllFeatures() {
        return this.getCurrentConfig();
    }

    /**
     * Get simplified configuration object (for homepage components)
     */
    getConfig() {
        const features = this.getAllFeatures();
        return {
            voiceprintRecognition: features.voiceprintRecognition?.enabled || false,
            voiceClone: features.voiceClone?.enabled || false,
            knowledgeBase: features.knowledgeBase?.enabled || false,
            mcpAccessPoint: features.mcpAccessPoint?.enabled || false,
            vad: features.vad?.enabled || false,
            asr: features.asr?.enabled || false,
            addressBook: features.addressBook?.enabled || false
        };
    }

    /**
     * Get the status of a specified feature
     */
    getFeatureStatus(featureKey) {
        const features = this.getAllFeatures();
        return features[featureKey]?.enabled || false;
    }

    /**
     * Set feature status
     */
    setFeatureStatus(featureKey, enabled) {
        const features = this.getAllFeatures();
        if (features[featureKey]) {
            features[featureKey].enabled = enabled;
            this.saveConfig(features);
            return true;
        }
        return false;
    }

    /**
     * Enable feature
     */
    enableFeature(featureKey) {
        return this.setFeatureStatus(featureKey, true);
    }

    /**
     * Disable feature
     */
    disableFeature(featureKey) {
        return this.setFeatureStatus(featureKey, false);
    }

    /**
     * Toggle feature status
     */
    toggleFeature(featureKey) {
        const currentStatus = this.getFeatureStatus(featureKey);
        return this.setFeatureStatus(featureKey, !currentStatus);
    }

    /**
     * Reset all features to default status
     */
    resetToDefault() {
        this.saveConfig(this.defaultFeatures);
    }

    /**
     * Batch update feature statuses
     */
    updateFeatures(featureUpdates) {
        const features = this.getAllFeatures();
        Object.keys(featureUpdates).forEach(featureKey => {
            if (features[featureKey]) {
                features[featureKey].enabled = featureUpdates[featureKey];
            } else if (this.defaultFeatures[featureKey]) {
                features[featureKey] = { ...this.defaultFeatures[featureKey] };
                features[featureKey].enabled = featureUpdates[featureKey];
            }
        });
        this.saveConfig(features);
    }

    /**
     * Get list of enabled features
     */
    getEnabledFeatures() {
        const features = this.getAllFeatures();
        return Object.keys(features).filter(key => features[key].enabled);
    }

    /**
     * Check if feature is enabled
     */
    isFeatureEnabled(featureKey) {
        return this.getFeatureStatus(featureKey);
    }
}

// Create singleton instance
const featureManager = new FeatureManager();

export default featureManager;