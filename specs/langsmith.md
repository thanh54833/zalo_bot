# Cấu hình LangSmith

## 1. Cài đặt

```bash
pip install langsmith
```

## 2. Cấu hình Environment Variables

```bash
export LANGCHAIN_API_KEY="lsv2_pt_8390b2e1eea14d7e9a84d80a5e0467a5_149781903"
export LANGCHAIN_ENDPOINT="https://api.smith.langchain.com" 
export LANGCHAIN_PROJECT="chatbot"  # Optional
```

## 3. Tích hợp với LangChain

```python
import os
from langchain.callbacks.tracers import LangChainTracer
from langchain.smith import RunEvalConfig

# Khởi tạo tracer
tracer = LangChainTracer(
    project_name=os.getenv("LANGCHAIN_PROJECT", "default")
)

# Sử dụng trong chain
chain = LLMChain(
    llm=llm,
    prompt=prompt,
    callbacks=[tracer]
)
```

## 4. Monitoring và Evaluation

### 4.1. Theo dõi runs

```python
from langsmith import Client

client = Client()
runs = client.list_runs(
    project_name="your-project",
    execution_order=1,  # Get only root runs
)
```

### 4.2. Đánh giá chains

```python
eval_config = RunEvalConfig(
    evaluators=[
        "qa",  # Built-in QA evaluator
        "criteria",  # Custom criteria
    ]
)

# Run evaluation
client.run_evaluation(
    project_name="your-project",
    eval_config=eval_config
)
```

## 5. Best Practices

1. **Project Organization**
   - Tạo project riêng cho mỗi use case
   - Sử dụng tags để phân loại runs

2. **Monitoring**
   - Theo dõi latency và token usage
   - Set up alerts cho các metrics quan trọng

3. **Security**
   - Không commit API keys
   - Sử dụng environment variables
   - Kiểm soát access rights

4. **Testing**
   - Unit tests cho custom evaluators
   - Integration tests với test datasets
   - Regression testing khi update models

## 6. Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Trace specific runs
run = client.get_run("run-id")
print(run.trace())
```

## 7. API Reference

- **Client Methods**
  - `list_runs()`
  - `create_run()`
  - `update_run()`
  - `get_run()`
  - `run_evaluation()`

- **Callback Options**
  - `on_llm_start`
  - `on_llm_end`
  - `on_chain_start`
  - `on_chain_end`
  - `on_tool_start`
  - `on_tool_end`

## 8. Troubleshooting

1. **API Key Issues**
   - Kiểm tra environment variables
   - Verify API key validity

2. **Connection Issues**
   - Check network connectivity
   - Verify endpoint URL

3. **Project Access**
   - Verify project permissions
   - Check organization settings

## 9. Resources

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [API Reference](https://api.smith.langchain.com/docs)
- [GitHub Repository](https://github.com/langchain-ai/langsmith)
- [Community Forum](https://github.com/langchain-ai/langsmith/discussions)
