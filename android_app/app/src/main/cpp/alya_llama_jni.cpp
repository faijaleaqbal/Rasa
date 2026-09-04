#include <android/log.h>
#include <jni.h>
#include <iomanip>
#include <cmath>
#include <string>
#include <vector>
#include <sstream>
#include <atomic>
#include <memory>
#include <mutex>
#include <chrono>
#include <unistd.h>
#include <dlfcn.h>

#include "logging.h"
#include "chat.h"
#include "common.h"
#include "sampling.h"
#include "llama.h"
#include "ggml-backend.h"

constexpr int   N_THREADS_MIN           = 2;
constexpr int   N_THREADS_MAX           = 8;
constexpr int   N_THREADS_HEADROOM      = 2;
constexpr int   DEFAULT_CONTEXT_SIZE    = 2048;
constexpr int   DEFAULT_BATCH_SIZE      = 512;
constexpr int   OVERFLOW_HEADROOM       = 4;
constexpr float DEFAULT_SAMPLER_TEMP    = 0.7f;
constexpr float DEFAULT_TOP_P           = 0.9f;
constexpr int   DEFAULT_TOP_K           = 40;
constexpr float DEFAULT_MIN_P           = 0.05f;
constexpr float DEFAULT_REPEAT_PENALTY  = 1.1f;
constexpr float DEFAULT_PRESENCE_PEN    = 0.0f;
constexpr float DEFAULT_FREQ_PEN        = 0.0f;

struct AlyaLlamaContext {
    llama_model* model = nullptr;
    llama_context* ctx = nullptr;
    llama_batch batch{};
    common_chat_templates_ptr chat_templates = nullptr;
    common_sampler* sampler = nullptr;

    std::vector<common_chat_msg> chat_msgs;
    llama_pos system_prompt_position = 0;
    llama_pos current_position = 0;
    llama_pos stop_generation_position = 0;
    std::string cached_token_chars;
    std::ostringstream assistant_ss;
    std::atomic<bool> cancel_flag{false};
    std::atomic<bool> is_generating{false};
    std::mutex context_mutex;

    int n_ctx = DEFAULT_CONTEXT_SIZE;
    int n_batch = DEFAULT_BATCH_SIZE;
    int n_ubatch = DEFAULT_BATCH_SIZE;
    int n_threads = 4;
    int n_gpu_layers = 0;
    uint64_t param_count = 0;
    uint64_t model_bytes = 0;
    std::string model_desc;
    std::string architecture;
    std::string quantization;
    std::string active_backend_name = "CPU";

    // Performance telemetry (PocketPal-style metrics)
    int64_t t_prompt_start_us = 0;
    int64_t t_prompt_eval_us = 0;
    int prompt_tokens_count = 0;
    int64_t t_first_token_us = 0;
    int64_t t_gen_start_us = 0;
    int64_t t_gen_eval_us = 0;
    int gen_tokens_count = 0;
};

static bool is_valid_utf8(const char *string) {
    if (!string) return true;
    const auto *bytes = (const unsigned char *) string;
    int num;
    while (*bytes != 0x00) {
        if ((*bytes & 0x80) == 0x00) {
            num = 1;
        } else if ((*bytes & 0xE0) == 0xC0) {
            num = 2;
        } else if ((*bytes & 0xF0) == 0xE0) {
            num = 3;
        } else if ((*bytes & 0xF8) == 0xF0) {
            num = 4;
        } else {
            return false;
        }
        bytes += 1;
        for (int i = 1; i < num; ++i) {
            if ((*bytes & 0xC0) != 0x80) return false;
            bytes += 1;
        }
    }
    return true;
}

static bool abort_callback_fn(void * data) {
    auto * instance = reinterpret_cast<AlyaLlamaContext*>(data);
    if (!instance) return false;
    return instance->cancel_flag.load();
}

static void shift_context(AlyaLlamaContext* instance) {
    const int n_discard = (instance->current_position - instance->system_prompt_position) / 2;
    LOGi("%s: Discarding %d tokens for context shift", __func__, n_discard);
    llama_memory_seq_rm(llama_get_memory(instance->ctx), 0, instance->system_prompt_position, instance->system_prompt_position + n_discard);
    llama_memory_seq_add(llama_get_memory(instance->ctx), 0, instance->system_prompt_position + n_discard, instance->current_position, -n_discard);
    instance->current_position -= n_discard;
    LOGi("%s: Context shift completed. Current pos: %d", __func__, instance->current_position);
}

static int decode_tokens(AlyaLlamaContext* instance, const llama_tokens &tokens, const llama_pos start_pos, const bool compute_last_logit = false) {
    const int batch_limit = instance->n_batch > 0 ? instance->n_batch : DEFAULT_BATCH_SIZE;
    for (int i = 0; i < (int) tokens.size(); i += batch_limit) {
        if (instance->cancel_flag.load()) return -1;
        const int cur_batch_size = std::min((int) tokens.size() - i, batch_limit);
        common_batch_clear(instance->batch);

        if (start_pos + i + cur_batch_size >= instance->n_ctx - OVERFLOW_HEADROOM) {
            LOGw("%s: Context near capacity, shifting...", __func__);
            shift_context(instance);
        }

        for (int j = 0; j < cur_batch_size; j++) {
            const llama_token token_id = tokens[i + j];
            const llama_pos position = start_pos + i + j;
            const bool want_logit = compute_last_logit && (i + j == (int) tokens.size() - 1);
            common_batch_add(instance->batch, token_id, position, {0}, want_logit);
        }

        const int res = llama_decode(instance->ctx, instance->batch);
        if (res != 0) {
            LOGe("%s: llama_decode failed with error code: %d", __func__, res);
            return res;
        }
    }
    return 0;
}

extern "C" {

JNIEXPORT jboolean JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeInit(JNIEnv *env, jclass, jstring jNativeLibDir) {
    llama_log_set(alya_android_log_callback, nullptr);
    if (jNativeLibDir != nullptr) {
        const char *nativeLibDir = env->GetStringUTFChars(jNativeLibDir, nullptr);
        if (nativeLibDir && nativeLibDir[0] != '\0') {
            LOGi("Loading backends from path: %s", nativeLibDir);
            ggml_backend_load_all_from_path(nativeLibDir);
        }
        env->ReleaseStringUTFChars(jNativeLibDir, nativeLibDir);
    }
    llama_backend_init();
    LOGi("Alya llama.cpp backend initialized successfully");
    return JNI_TRUE;
}

JNIEXPORT jstring JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeGetBackendDevices(JNIEnv *env, jclass) {
    std::ostringstream ss;
    ss << "[";
    bool first = true;

    size_t count = ggml_backend_reg_count();
    for (size_t i = 0; i < count; ++i) {
        ggml_backend_reg_t reg = ggml_backend_reg_get(i);
        if (!reg) continue;
        const char *reg_name = ggml_backend_reg_name(reg);
        size_t dev_count = ggml_backend_reg_dev_count(reg);

        for (size_t d = 0; d < dev_count; ++d) {
            ggml_backend_dev_t dev = ggml_backend_reg_dev_get(reg, d);
            if (!dev) continue;

            const char *dev_name = ggml_backend_dev_name(dev);
            const char *dev_desc = ggml_backend_dev_description(dev);
            enum ggml_backend_dev_type dev_type = ggml_backend_dev_type(dev);

            std::string type_str = "CPU";
            if (dev_type == GGML_BACKEND_DEVICE_TYPE_GPU || dev_type == GGML_BACKEND_DEVICE_TYPE_IGPU) {
                type_str = "GPU";
            } else if (dev_type == GGML_BACKEND_DEVICE_TYPE_ACCEL) {
                type_str = "NPU";
            }

            if (!first) ss << ",";
            first = false;

            ss << "{"
               << "\"type\":\"" << type_str << "\","
               << "\"name\":\"" << (dev_name ? dev_name : (reg_name ? reg_name : "CPU")) << "\","
               << "\"description\":\"" << (dev_desc ? dev_desc : "") << "\","
               << "\"backend\":\"" << (reg_name ? reg_name : "") << "\""
               << "}";
        }
    }

    if (first) {
        ss << "{"
           << "\"type\":\"CPU\","
           << "\"name\":\"CPU (ARM NEON)\","
           << "\"description\":\"ARM64 Optimized CPU Backend\","
           << "\"backend\":\"CPU\""
           << "}";
    }

    ss << "]";
    return env->NewStringUTF(ss.str().c_str());
}

JNIEXPORT jlong JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeLoadModel(
        JNIEnv *env, jclass,
        jstring jModelPath,
        jint jThreads,
        jint jCtx,
        jint jBatch,
        jint jUBatch,
        jint jGpuLayers,
        jboolean jUseMmap,
        jboolean jUseMlock,
        jboolean jFlashAttn,
        jint jCacheTypeK,
        jint jCacheTypeV,
        jfloat jTemp,
        jfloat jTopP,
        jint jTopK,
        jfloat jRepeatPenalty) {

    if (jModelPath == nullptr) return -1;
    const char *model_path = env->GetStringUTFChars(jModelPath, nullptr);
    LOGi("Loading local model from: %s (gpu_layers: %d, ctx: %d)", model_path, jGpuLayers, jCtx);

    llama_model_params model_params = llama_model_default_params();
    model_params.n_gpu_layers = jGpuLayers;

    if (jUseMmap && jUseMlock) {
        model_params.load_mode = LLAMA_LOAD_MODE_MMAP_MLOCK;
    } else if (jUseMmap) {
        model_params.load_mode = LLAMA_LOAD_MODE_MMAP;
    } else if (jUseMlock) {
        model_params.load_mode = LLAMA_LOAD_MODE_MLOCK;
    } else {
        model_params.load_mode = LLAMA_LOAD_MODE_NONE;
    }

    llama_model* model = llama_model_load_from_file(model_path, model_params);
    env->ReleaseStringUTFChars(jModelPath, model_path);

    if (!model) {
        LOGe("Failed to load model from file: %s", model_path);
        return -1;
    }

    uint64_t n_params = llama_model_n_params(model);
    LOGi("Model loaded successfully. Total parameters: %llu (No artificial size limits)", (unsigned long long) n_params);

    auto* instance = new AlyaLlamaContext();
    instance->model = model;
    instance->param_count = n_params;
    instance->model_bytes = llama_model_size(model);
    instance->n_gpu_layers = jGpuLayers;

    char desc_buf[256];
    llama_model_desc(model, desc_buf, sizeof(desc_buf));
    instance->model_desc = desc_buf;

    enum llama_ftype ftype = llama_model_ftype(model);
    const char* ftype_name = llama_ftype_name(ftype);
    instance->quantization = (ftype_name ? ftype_name : "UNKNOWN");

    int n_threads = jThreads;
    if (n_threads <= 0) {
        n_threads = std::max(N_THREADS_MIN, std::min(N_THREADS_MAX, (int) sysconf(_SC_NPROCESSORS_ONLN) - N_THREADS_HEADROOM));
    }
    instance->n_threads = n_threads;

    int n_ctx = jCtx > 0 ? jCtx : DEFAULT_CONTEXT_SIZE;
    int train_ctx = llama_model_n_ctx_train(model);
    if (train_ctx > 0 && n_ctx > train_ctx) {
        n_ctx = train_ctx;
    }
    instance->n_ctx = n_ctx;

    int n_batch = (jBatch > 0) ? jBatch : DEFAULT_BATCH_SIZE;
    int n_ubatch = (jUBatch > 0) ? jUBatch : DEFAULT_BATCH_SIZE;
    instance->n_batch = n_batch;
    instance->n_ubatch = n_ubatch;

    llama_context_params ctx_params = llama_context_default_params();
    ctx_params.n_ctx = n_ctx;
    ctx_params.n_batch = n_batch;
    ctx_params.n_ubatch = n_ubatch;
    ctx_params.n_threads = n_threads;
    ctx_params.n_threads_batch = n_threads;
    ctx_params.flash_attn_type = jFlashAttn ? LLAMA_FLASH_ATTN_TYPE_ENABLED : LLAMA_FLASH_ATTN_TYPE_DISABLED;

    if (jCacheTypeK > 0) {
        ctx_params.type_k = static_cast<enum ggml_type>(jCacheTypeK);
    }
    if (jCacheTypeV > 0) {
        ctx_params.type_v = static_cast<enum ggml_type>(jCacheTypeV);
    }

    ctx_params.abort_callback = abort_callback_fn;
    ctx_params.abort_callback_data = instance;

    instance->ctx = llama_init_from_model(model, ctx_params);
    if (!instance->ctx) {
        LOGe("Failed to initialize llama_context from model");
        llama_model_free(model);
        delete instance;
        return -3;
    }

    instance->batch = llama_batch_init(n_batch, 0, 1);
    instance->chat_templates = common_chat_templates_init(model, "");

    common_params_sampling sparams;
    sparams.temp = (jTemp > 0.0f) ? jTemp : DEFAULT_SAMPLER_TEMP;
    sparams.top_p = (jTopP > 0.0f) ? jTopP : DEFAULT_TOP_P;
    sparams.top_k = (jTopK > 0) ? jTopK : DEFAULT_TOP_K;
    sparams.min_p = DEFAULT_MIN_P;
    sparams.penalty_repeat = (jRepeatPenalty > 0.0f) ? jRepeatPenalty : DEFAULT_REPEAT_PENALTY;
    sparams.penalty_present = DEFAULT_PRESENCE_PEN;
    sparams.penalty_freq = DEFAULT_FREQ_PEN;

    instance->sampler = common_sampler_init(model, sparams);

    if (jGpuLayers > 0) {
        instance->active_backend_name = "GPU (Offloaded " + std::to_string(jGpuLayers) + " layers)";
    } else {
        instance->active_backend_name = "CPU (" + std::to_string(n_threads) + " threads)";
    }

    LOGi("AlyaLlamaContext ready. Context: %d, Batch: %d, Threads: %d, Backend: %s",
         n_ctx, n_batch, n_threads, instance->active_backend_name.c_str());
    return reinterpret_cast<jlong>(instance);
}

JNIEXPORT jint JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeProcessSystemPrompt(
        JNIEnv *env, jclass, jlong handle, jstring jPrompt) {
    auto* instance = reinterpret_cast<AlyaLlamaContext*>(handle);
    if (!instance || !instance->ctx) return -1;

    std::lock_guard<std::mutex> lock(instance->context_mutex);

    instance->chat_msgs.clear();
    instance->system_prompt_position = 0;
    instance->current_position = 0;
    instance->cached_token_chars.clear();
    instance->assistant_ss.str("");
    llama_memory_clear(llama_get_memory(instance->ctx), false);

    if (jPrompt == nullptr) return 0;
    const char *prompt_str = env->GetStringUTFChars(jPrompt, nullptr);
    std::string prompt(prompt_str);
    env->ReleaseStringUTFChars(jPrompt, prompt_str);

    if (prompt.empty()) return 0;

    std::string formatted_prompt = prompt;
    bool has_template = common_chat_templates_was_explicit(instance->chat_templates.get());
    if (has_template) {
        common_chat_msg msg;
        msg.role = "system";
        msg.content = prompt;
        formatted_prompt = common_chat_format_single(instance->chat_templates.get(), instance->chat_msgs, msg, false, false);
        instance->chat_msgs.push_back(msg);
    }

    const auto tokens = common_tokenize(instance->ctx, formatted_prompt, has_template, has_template);
    if ((int) tokens.size() >= instance->n_ctx - OVERFLOW_HEADROOM) {
        LOGe("System prompt exceeds context size (%d tokens)", (int) tokens.size());
        return -2;
    }

    int res = decode_tokens(instance, tokens, 0);
    if (res == 0) {
        instance->system_prompt_position = (int) tokens.size();
        instance->current_position = instance->system_prompt_position;
    }
    return res;
}

JNIEXPORT jint JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeProcessUserPrompt(
        JNIEnv *env, jclass, jlong handle, jstring jPrompt, jint nPredict) {
    auto* instance = reinterpret_cast<AlyaLlamaContext*>(handle);
    if (!instance || !instance->ctx) return -1;

    std::lock_guard<std::mutex> lock(instance->context_mutex);

    instance->cancel_flag.store(false);
    instance->is_generating.store(true);
    instance->cached_token_chars.clear();
    instance->assistant_ss.str("");

    if (jPrompt == nullptr) return -1;
    const char *prompt_str = env->GetStringUTFChars(jPrompt, nullptr);
    std::string user_prompt(prompt_str);
    env->ReleaseStringUTFChars(jPrompt, prompt_str);

    if (user_prompt.empty()) return -1;

    std::string formatted_prompt = user_prompt;
    bool has_template = common_chat_templates_was_explicit(instance->chat_templates.get());
    if (has_template) {
        common_chat_msg msg;
        msg.role = "user";
        msg.content = user_prompt;
        formatted_prompt = common_chat_format_single(instance->chat_templates.get(), instance->chat_msgs, msg, true, false);
        instance->chat_msgs.push_back(msg);
    }

    auto tokens = common_tokenize(instance->ctx, formatted_prompt, has_template, has_template);
    const int max_allowed = instance->n_ctx - OVERFLOW_HEADROOM;
    if ((int) tokens.size() > max_allowed) {
        tokens.resize(max_allowed);
    }

    instance->t_prompt_start_us = llama_time_us();
    int res = decode_tokens(instance, tokens, instance->current_position, true);
    if (res != 0) {
        instance->is_generating.store(false);
        return res;
    }

    instance->t_prompt_eval_us = llama_time_us() - instance->t_prompt_start_us;
    instance->prompt_tokens_count = (int) tokens.size();
    instance->t_gen_start_us = llama_time_us();
    instance->t_first_token_us = 0;
    instance->gen_tokens_count = 0;
    instance->t_gen_eval_us = 0;

    instance->current_position += (int) tokens.size();
    instance->stop_generation_position = instance->current_position + (nPredict > 0 ? nPredict : 1024);
    return 0;
}

JNIEXPORT jstring JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeGenerateNextToken(JNIEnv *env, jclass, jlong handle) {
    auto* instance = reinterpret_cast<AlyaLlamaContext*>(handle);
    if (!instance || !instance->ctx || !instance->sampler) return nullptr;

    std::lock_guard<std::mutex> lock(instance->context_mutex);

    if (instance->cancel_flag.load()) {
        LOGi("Generation cancelled by user via stopCompletion");
        instance->is_generating.store(false);
        return nullptr;
    }

    if (instance->current_position >= instance->n_ctx - OVERFLOW_HEADROOM) {
        shift_context(instance);
    }

    if (instance->current_position >= instance->stop_generation_position) {
        instance->is_generating.store(false);
        return nullptr;
    }

    const llama_token token_id = common_sampler_sample(instance->sampler, instance->ctx, -1);
    common_sampler_accept(instance->sampler, token_id, true);

    common_batch_clear(instance->batch);
    common_batch_add(instance->batch, token_id, instance->current_position, {0}, true);

    if (llama_decode(instance->ctx, instance->batch) != 0) {
        LOGe("llama_decode failed during next token generation");
        instance->is_generating.store(false);
        return nullptr;
    }

    if (instance->gen_tokens_count == 0) {
        instance->t_first_token_us = llama_time_us();
    }

    instance->current_position++;
    instance->gen_tokens_count++;
    instance->t_gen_eval_us = llama_time_us() - instance->t_gen_start_us;

    if (llama_vocab_is_eog(llama_model_get_vocab(instance->model), token_id)) {
        common_chat_msg assistant_msg;
        assistant_msg.role = "assistant";
        assistant_msg.content = instance->assistant_ss.str();
        instance->chat_msgs.push_back(assistant_msg);
        instance->is_generating.store(false);
        return nullptr;
    }

    auto piece = common_token_to_piece(instance->ctx, token_id);
    instance->cached_token_chars += piece;

    if (is_valid_utf8(instance->cached_token_chars.c_str())) {
        jstring result = env->NewStringUTF(instance->cached_token_chars.c_str());
        instance->assistant_ss << instance->cached_token_chars;
        instance->cached_token_chars.clear();
        return result;
    } else {
        return env->NewStringUTF("");
    }
}

JNIEXPORT void JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeCancel(JNIEnv *, jclass, jlong handle) {
    auto* instance = reinterpret_cast<AlyaLlamaContext*>(handle);
    if (instance) {
        instance->cancel_flag.store(true);
        instance->is_generating.store(false);
        LOGi("PocketPal-style stopCompletion cancellation triggered");
    }
}

JNIEXPORT jlong JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeGetParamCount(JNIEnv *, jclass, jlong handle) {
    auto* instance = reinterpret_cast<AlyaLlamaContext*>(handle);
    return instance ? (jlong) instance->param_count : 0;
}

JNIEXPORT jlong JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeGetModelSize(JNIEnv *, jclass, jlong handle) {
    auto* instance = reinterpret_cast<AlyaLlamaContext*>(handle);
    return instance ? (jlong) instance->model_bytes : 0;
}

JNIEXPORT jstring JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeGetModelDesc(JNIEnv *env, jclass, jlong handle) {
    auto* instance = reinterpret_cast<AlyaLlamaContext*>(handle);
    if (!instance) return env->NewStringUTF("");
    return env->NewStringUTF(instance->model_desc.c_str());
}

JNIEXPORT jstring JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeGetModelMetadata(JNIEnv *env, jclass, jlong handle) {
    auto* instance = reinterpret_cast<AlyaLlamaContext*>(handle);
    if (!instance || !instance->model) return env->NewStringUTF("{}");

    std::ostringstream ss;
    ss << "{"
       << "\"param_count\":" << instance->param_count << ","
       << "\"model_bytes\":" << instance->model_bytes << ","
       << "\"n_ctx\":" << instance->n_ctx << ","
       << "\"n_ctx_train\":" << llama_model_n_ctx_train(instance->model) << ","
       << "\"n_embd\":" << llama_model_n_embd(instance->model) << ","
       << "\"n_layer\":" << llama_model_n_layer(instance->model) << ","
       << "\"n_head\":" << llama_model_n_head(instance->model) << ","
       << "\"n_head_kv\":" << llama_model_n_head_kv(instance->model) << ","
       << "\"quantization\":\"" << instance->quantization << "\","
       << "\"desc\":\"" << instance->model_desc << "\","
       << "\"backend\":\"" << instance->active_backend_name << "\""
       << "}";

    return env->NewStringUTF(ss.str().c_str());
}

JNIEXPORT jstring JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeGetGenerationTimings(JNIEnv *env, jclass, jlong handle) {
    auto* instance = reinterpret_cast<AlyaLlamaContext*>(handle);
    if (!instance) return env->NewStringUTF("{}");

    double prompt_ms = instance->t_prompt_eval_us / 1000.0;
    double gen_ms = instance->t_gen_eval_us / 1000.0;
    double ttft_ms = (instance->t_first_token_us > 0) ? (instance->t_first_token_us - instance->t_prompt_start_us) / 1000.0 : prompt_ms;
    double prompt_tps = (prompt_ms > 0.0) ? (instance->prompt_tokens_count * 1000.0) / prompt_ms : 0.0;
    double gen_tps = (gen_ms > 0.0) ? (instance->gen_tokens_count * 1000.0) / gen_ms : 0.0;

    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2);
    ss << "{"
       << "\"prompt_ms\":" << prompt_ms << ","
       << "\"gen_ms\":" << gen_ms << ","
       << "\"ttft_ms\":" << ttft_ms << ","
       << "\"prompt_tokens\":" << instance->prompt_tokens_count << ","
       << "\"gen_tokens\":" << instance->gen_tokens_count << ","
       << "\"prompt_tps\":" << prompt_tps << ","
       << "\"gen_tps\":" << gen_tps << ","
       << "\"backend\":\"" << instance->active_backend_name << "\""
       << "}";

    return env->NewStringUTF(ss.str().c_str());
}

JNIEXPORT void JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeUnloadModel(JNIEnv *, jclass, jlong handle) {
    auto* instance = reinterpret_cast<AlyaLlamaContext*>(handle);
    if (!instance) return;

    LOGi("Unloading model context and releasing memory");
    instance->cancel_flag.store(true);
    instance->is_generating.store(false);

    std::lock_guard<std::mutex> lock(instance->context_mutex);

    if (instance->sampler) {
        common_sampler_free(instance->sampler);
        instance->sampler = nullptr;
    }
    instance->chat_templates.reset();
    llama_batch_free(instance->batch);
    if (instance->ctx) {
        llama_free(instance->ctx);
        instance->ctx = nullptr;
    }
    if (instance->model) {
        llama_model_free(instance->model);
        instance->model = nullptr;
    }
    delete instance;
    LOGi("Model memory successfully freed");
}

JNIEXPORT void JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeShutdown(JNIEnv *, jclass) {
    llama_backend_free();
    LOGi("llama_backend_free executed");
}

JNIEXPORT jstring JNICALL
Java_com_alya_aiagent_local_LlamaNative_nativeSystemInfo(JNIEnv *env, jclass) {
    return env->NewStringUTF(llama_print_system_info());
}

} // extern "C"
