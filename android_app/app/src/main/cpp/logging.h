#pragma once
#include <android/log.h>
#include "ggml.h"

#define TAG "AlyaLlama"

#define LOGv(...) __android_log_print(ANDROID_LOG_VERBOSE, TAG, __VA_ARGS__)
#define LOGd(...) __android_log_print(ANDROID_LOG_DEBUG,   TAG, __VA_ARGS__)
#define LOGi(...) __android_log_print(ANDROID_LOG_INFO,    TAG, __VA_ARGS__)
#define LOGw(...) __android_log_print(ANDROID_LOG_WARN,    TAG, __VA_ARGS__)
#define LOGe(...) __android_log_print(ANDROID_LOG_ERROR,   TAG, __VA_ARGS__)

static void alya_android_log_callback(ggml_log_level level, const char * text, void * user_data) {
    (void) user_data;
    switch (level) {
        case GGML_LOG_LEVEL_ERROR: LOGe("%s", text); break;
        case GGML_LOG_LEVEL_WARN:  LOGw("%s", text); break;
        case GGML_LOG_LEVEL_INFO:  LOGi("%s", text); break;
        case GGML_LOG_LEVEL_DEBUG: LOGd("%s", text); break;
        default:                   LOGv("%s", text); break;
    }
}
