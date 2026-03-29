namespace AgentLens.Integrations;

/// <summary>
/// Microsoft Semantic Kernel integration for AgentLens.
/// Hooks into SK's function invocation pipeline to automatically create spans
/// for every kernel function call.
///
/// Usage (once SK API stabilises):
///   SemanticKernelIntegration.Patch();
///
/// Requires: Microsoft.SemanticKernel (not a dependency of AgentLens.Observe itself —
/// callers must reference SK separately).
/// </summary>
public static class SemanticKernelIntegration
{
    private static bool _patched;

    /// <summary>
    /// Installs AgentLens hooks into the Semantic Kernel function invocation
    /// pipeline via IFunctionInvocationFilter.
    ///
    /// This is a placeholder implementation. Full wiring will be completed once
    /// the IFunctionInvocationFilter API stabilises in Microsoft.SemanticKernel
    /// (tracked: https://github.com/microsoft/semantic-kernel).
    ///
    /// Current behaviour: no-op, logs a debug message.
    /// </summary>
    public static void Patch()
    {
        if (_patched) return;
        _patched = true;

        // TODO(integration): Register an IFunctionInvocationFilter on the Kernel
        // instance that wraps each function call with AgentLensClient.Span().
        // Blocked on SK stabilising the filter API across kernel instances.
        //
        // Intended implementation sketch:
        //   kernel.FunctionInvocationFilters.Add(new AgentLensSkFilter());
        //
        // AgentLensSkFilter.OnFunctionInvocationAsync would:
        //   1. Read context.Function.Name and context.Function.PluginName
        //   2. Open AgentLensClient.Span($"{pluginName}.{functionName}", "sk_function")
        //   3. Await context.Next()
        //   4. Record output and dispose span

        System.Diagnostics.Debug.WriteLine(
            "[AgentLens] SemanticKernelIntegration.Patch() called — " +
            "full implementation pending SK filter API stabilisation.");
    }
}
