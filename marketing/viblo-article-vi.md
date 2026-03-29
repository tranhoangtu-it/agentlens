# Tôi đã xây dựng Chrome DevTools cho AI Agents — AgentLens

*Đăng trên Viblo.asia*

---

Xin chào cộng đồng Viblo! Tôi là Tú, và tôi muốn chia sẻ về dự án open-source mà tôi đã xây dựng: **AgentLens** — một nền tảng observability self-hosted cho AI agents.

## Vấn đề

Nếu bạn đang xây dựng AI agents (sử dụng LangChain, CrewAI, AutoGen, hay bất kỳ framework nào), bạn sẽ gặp một vấn đề: **khi agent fail, bạn không biết tại sao.**

Logs cho bạn thấy API calls và timestamps. Nhưng nó không trả lời được:
- Tại sao agent chọn tool A thay vì tool B?
- Ở đâu chính xác reasoning bị sai?
- Đó là context window overflow hay hallucinated tool call?

Tôi đã debug hàng trăm agent failures. Mỗi lần mất hàng giờ đọc trace logs.

## Giải pháp: AgentLens

AgentLens ghi lại mọi bước trong quá trình thực thi của agent và cho phép bạn:

### 1. Trace Everything
Chỉ cần 2 dòng code:

```python
import agentlens

@agentlens.trace
def my_agent(query):
    # Mọi tool call, LLM call đều được ghi lại tự động
    pass
```

### 2. Replay như Flight Recorder
Xem lại từng bước thực thi của agent. Di chuyển qua timeline, thấy chính xác điều gì xảy ra ở mỗi thời điểm.

### 3. AI Autopsy (Feature độc quyền)
Click "Autopsy" trên bất kỳ trace nào bị fail → AI phân tích toàn bộ execution tree và cho bạn biết:
- **Root cause**: "Context window overflow ở step 4"
- **Severity**: Critical
- **Suggested fix**: "Thêm summarization step giữa search và analysis"

**Không tool nào khác có feature này** — không LangSmith, không Langfuse.

### 4. MCP Protocol Tracing
Nếu bạn đang dùng MCP (Model Context Protocol) — AgentLens là tool duy nhất trace được MCP calls.

### 5. Nhiều hơn nữa
- Prompt versioning (quản lý version prompt)
- LLM-as-Judge evaluation (đánh giá chất lượng tự động)
- Cost tracking per model
- Alerting (webhook khi vượt ngưỡng)
- Plugin system

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + SQLModel (Python) |
| Frontend | React 19 + Vite + Tailwind CSS |
| Database | SQLite (dev) / PostgreSQL (prod) |
| SDKs | Python, TypeScript, .NET 8 |
| CLI | Go (Cobra) |
| IDE | VS Code Extension |
| Deploy | Docker (`docker compose up`) |

## Tại sao Self-Hosted?

- **Miễn phí mãi mãi**, không giới hạn traces
- **Dữ liệu không rời khỏi server của bạn** — quan trọng khi traces chứa sensitive data
- **Không vendor lock-in**
- **Không per-seat pricing**

## So sánh với đối thủ

| Feature | AgentLens | LangSmith | Langfuse |
|---------|-----------|-----------|----------|
| Self-hosted | Có (miễn phí) | Không | Có (limited) |
| AI Failure Autopsy | Có | Không | Không |
| MCP Tracing | Có | Không | Không |
| .NET SDK | Có | Không | Không |
| Giá | Miễn phí | $39/seat/tháng | Free tier limited |

## Bắt đầu

```bash
pip install agentlens-observe
docker compose up  # Dashboard tại http://localhost:3000
```

## Đóng góp

Dự án hoàn toàn open-source. Mọi contribution đều welcome!

GitHub: https://github.com/tranhoangtu-it/agentlens

---

Nếu bạn đang build AI agents và gặp khó khăn trong debugging, hãy thử AgentLens. Star trên GitHub nếu thấy hữu ích — mỗi star giúp dự án open-source có thêm động lực!

*Tags: #AI #OpenSource #DevTools #Python #Observability*
