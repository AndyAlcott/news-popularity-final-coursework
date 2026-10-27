package com.example.news;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class NewsController {
    private final RecordMapper records;
    private final StringRedisTemplate redis;
    private final ObjectMapper json;
    @Value("${news.python}") private String python;
    @Value("${news.analysis}") private String analysis;

    public NewsController(RecordMapper records, StringRedisTemplate redis, ObjectMapper json) {
        this.records = records;
        this.redis = redis;
        this.json = json;
    }

    @GetMapping("/schema")
    public JsonNode schema() throws Exception {
        return json.readTree(Files.readString(Path.of(analysis, "models/features.json")));
    }

    @GetMapping("/sample")
    public JsonNode sample() throws Exception {
        return json.readTree(Files.readString(Path.of(analysis, "results/sample_input.json")));
    }

    @GetMapping("/metrics")
    public Map<String, Object> metrics() throws Exception {
        // 缓存训练结果，避免重复读取文件；十分钟后自动失效。
        String value = redis.opsForValue().get("news:metrics:v1");
        boolean hit = value != null;
        if (!hit) {
            value = Files.readString(Path.of(analysis, "results/metrics.json"));
            redis.opsForValue().set("news:metrics:v1", value, Duration.ofMinutes(10));
        }
        return Map.of("cached", hit, "data", json.readTree(value));
    }

    @GetMapping("/quality")
    public JsonNode quality() throws Exception {
        return json.readTree(Files.readString(Path.of(analysis, "results/data_quality.json")));
    }

    @GetMapping(value = "/figure/{name}", produces = "image/png")
    public byte[] figure(@PathVariable String name) throws Exception {
        if (!List.of("01_class_distribution", "02_boxplots", "03_correlation", "04_confusion_decision_tree",
                     "04_confusion_random_forest", "05_feature_importance", "06_model_comparison").contains(name)) {
            throw new IllegalArgumentException("图表不存在");
        }
        return Files.readAllBytes(Path.of(analysis, "results", name + ".png"));
    }

    @PostMapping("/predict")
    public Map<String, Object> predict(@RequestBody JsonNode request) throws Exception {
        if (!request.has("features") || !request.get("features").isObject()) {
            throw new IllegalArgumentException("请完整填写新闻特征");
        }
        // 参数通过标准输入传递，不拼接系统命令；模型及校验逻辑由 Python 复用。
        ProcessBuilder builder = new ProcessBuilder(python, Path.of(analysis, "predict.py").toAbsolutePath().toString());
        builder.environment().put("PYTHONIOENCODING", "utf-8");
        Process process = builder.redirectError(ProcessBuilder.Redirect.INHERIT).start();
        try (var input = process.getOutputStream()) {
            input.write(json.writeValueAsBytes(request));
        }
        if (!process.waitFor(30, TimeUnit.SECONDS)) {
            process.destroyForcibly();
            throw new IllegalStateException("预测超时，请稍后重试");
        }
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        JsonNode result = json.readTree(output);
        if (result == null) throw new IllegalStateException("模型未返回结果");
        if (process.exitValue() != 0) throw new IllegalArgumentException(result.path("error").asText("输入无效"));
        Map<String, Object> record = new LinkedHashMap<>();
        record.put("model", result.get("model").asText());
        record.put("features", json.writeValueAsString(request.get("features")));
        record.put("label", result.get("label").asText());
        record.put("probability", result.get("probability").asDouble());
        records.insert(record);
        return record;
    }

    @GetMapping("/records")
    public List<Map<String, Object>> records() {
        return records.list();
    }

    @DeleteMapping("/records/{id}")
    public Map<String, Object> delete(@PathVariable long id) {
        return Map.of("deleted", records.delete(id) > 0);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<?> invalid(IllegalArgumentException error) {
        return ResponseEntity.badRequest().body(Map.of("error", error.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<?> unavailable(Exception error) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(Map.of("error", "服务暂不可用，请检查 MySQL、Redis、Python 路径及模型文件"));
    }
}
