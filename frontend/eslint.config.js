import js from '@eslint/js'
import vue from 'eslint-plugin-vue'

export default [
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: 'module',
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/no-deprecated-destroyed-lifecycle': 'off',
      'vue/require-explicit-emits': 'off',
    },
  },
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
]
