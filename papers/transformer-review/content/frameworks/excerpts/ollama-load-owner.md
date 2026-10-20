**源码摘录：区分请求事件、已加载模型与进行中的加载。** 仓库 `ollama`，固定提交 `42e911bc3d05798cad729cb474bf62f378cb2e26`；文件 `server/sched.go`，第 61–82 行，符号 `Scheduler`。[对应源码](https://github.com/ollama/ollama/blob/42e911bc3d05798cad729cb474bf62f378cb2e26/server/sched.go#L61-L82)。

```go
type Scheduler struct {
	pendingReqCh  chan *LlmRequest
	finishedReqCh chan *LlmRequest
	expiredCh     chan *runnerRef
	unloadedCh    chan any

	// loadedMu protects loaded and activeLoading
	loadedMu sync.Mutex

	// activeLoading is the model that we are currently working on loading,
	// including by evicting one or more other models. We can only load
	// one model at a time but new requests to models that already loaded can
	// happen in parallel
	activeLoading llm.LlamaServer
	loaded        map[string]*runnerRef

	loadFn          func(req *LlmRequest, systemInfo ml.SystemInfo, gpus []ml.DeviceInfo, requireFull bool) bool
	newServerFn     func(systemInfo ml.SystemInfo, gpus []ml.DeviceInfo, model string, f *gguf.Model, adapters []string, projectors []string, opts api.Options, numParallel int, config llm.LlamaServerConfig) (llm.LlamaServer, error)
	getGpuFn        func(ctx context.Context, runners []ml.FilteredRunnerDiscovery) []ml.DeviceInfo
	getSystemInfoFn func() ml.SystemInfo
	waitForRecovery time.Duration
}
```
