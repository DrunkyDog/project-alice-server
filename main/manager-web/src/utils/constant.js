const HAVE_NO_RESULT = '暂无'
export default {
    HAVE_NO_RESULT, // 项目的配置信息
    PAGE: {
        LOGIN: '/login',
    },
    STORAGE_KEY: {
        TOKEN: 'TOKEN',
        PUBLIC_KEY: 'PUBLIC_KEY',
        USER_TYPE: 'USER_TYPE'
    },
    Lang: {
        'zh_cn': 'Chinese Mandarin', 'zh_tw': 'Taiwanese Mandarin', 'en': 'English'
    },
    FONT_SIZE: {
        'big': 'Big',
        'normal': 'Normal',
    }, // 获取map中的某key
    get(map, key) {
        return map[key] || HAVE_NO_RESULT
    }
}
