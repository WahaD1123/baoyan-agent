import { MarkdownContent } from "./MarkdownContent";
import type { WorkflowRun, WorkflowStep } from "../types/domain";


type Props = {
  workflows: WorkflowRun[];
};

const statusLabels: Record<string, string> = {
  completed: "\u5df2\u5b8c\u6210",
  running: "\u6267\u884c\u4e2d",
  failed: "\u5931\u8d25",
  skipped: "\u5df2\u8df3\u8fc7",
  pending: "\u7b49\u5f85\u4e2d"
};

const kindLabels: Record<string, string> = {
  planner: "PLAN",
  tool: "TOOL",
  agent: "AGENT",
  condition: "IF"
};

const planSourceLabels: Record<string, string> = {
  planner: "Qwen Planner",
  fallback: "Fallback Plan",
  fixed: "Fixed Flow"
};

function StepFacts({ step }: { step: WorkflowStep }) {
  const facts = [
    step.agent_result?.agent_name,
    step.model_name ? `model: ${step.model_name}` : "",
    typeof step.duration_ms === "number" ? `${step.duration_ms} ms` : "",
    step.tool_call ? `transport: ${step.tool_call.transport}` : ""
  ].filter(Boolean);

  return facts.length ? <div className="traceFacts">{facts.map((fact) => <span key={fact}>{fact}</span>)}</div> : null;
}

export function WorkflowTraceList({ workflows }: Props) {
  return (
    <div className="workflowList">
      {workflows.slice(0, 20).map((workflow) => (
        <article className="workflowItem workflowTrace" key={workflow.id}>
          <div className="workflowTopline">
            <strong>{workflow.workflow_type}</strong>
            <span data-status={workflow.status}>{statusLabels[workflow.status] ?? workflow.status}</span>
          </div>

          <div className="workflowRunMeta">
            <span className="planSource" data-source={workflow.plan_source ?? "fixed"}>
              {planSourceLabels[workflow.plan_source ?? "fixed"] ?? workflow.plan_source}
            </span>
            <small>{workflow.steps.length} {"\u4e2a\u6b65\u9aa4"}</small>
          </div>
          {workflow.planner_summary ? <p className="plannerSummary">{workflow.planner_summary}</p> : null}

          <ol className="traceList">
            {workflow.steps.map((step, index) => (
              <li className={`traceStep trace-${step.status}`} key={`${workflow.id}-${index}-${step.name}`}>
                <div className="traceStepHeader">
                  <span className="traceKind" data-kind={step.step_type ?? "agent"}>
                    {kindLabels[step.step_type ?? "agent"] ?? "STEP"}
                  </span>
                  <div className="traceIdentity">
                    <strong>{step.capability || step.name}</strong>
                    {step.capability ? <small>{step.name}</small> : null}
                  </div>
                  <span className="traceStatus" data-status={step.status}>
                    {statusLabels[step.status] ?? step.status}
                  </span>
                </div>

                <StepFacts step={step} />
                {step.decision_reason ? <p className="traceReason">{step.decision_reason}</p> : null}
                {step.error ? <p className="traceError">{step.error}</p> : null}

                {step.tool_call ? (
                  <details className="toolTraceDetails">
                    <summary>{"\u67e5\u770b\u5de5\u5177\u8f68\u8ff9"}</summary>
                    <dl>
                      <div>
                        <dt>{"\u53c2\u6570"}</dt>
                        <dd><code>{step.tool_call.arguments_summary || "{}"}</code></dd>
                      </div>
                      <div>
                        <dt>{"\u8fd4\u56de\u6458\u8981"}</dt>
                        <dd><code>{step.tool_call.result_summary || "{}"}</code></dd>
                      </div>
                    </dl>
                    {step.tool_call.fallback_reason ? (
                      <p className="traceFallback">fallback: {step.tool_call.fallback_reason}</p>
                    ) : null}
                  </details>
                ) : null}
              </li>
            ))}
          </ol>

          <details className="workflowOutput">
            <summary>{"\u67e5\u770b\u6700\u7ec8\u8f93\u51fa"}</summary>
            <MarkdownContent content={workflow.final_result} />
          </details>
        </article>
      ))}
    </div>
  );
}
