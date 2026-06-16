import type { WorkflowRun } from "../types/domain";

type Props = {
  workflows: WorkflowRun[];
};

export function WorkflowList({ workflows }: Props) {
  return (
    <div className="workflowList">
      {workflows.map((workflow) => (
        <article className="workflowItem" key={workflow.id}>
          <div className="workflowTopline">
            <strong>{workflow.workflow_type}</strong>
            <span>{workflow.status}</span>
          </div>
          <p>{workflow.final_result}</p>
          <ol>
            {workflow.steps.map((step) => (
              <li key={`${workflow.id}-${step.name}`}>
                <span>{step.name}</span>
                <small>{step.agent_result?.agent_name ?? "System"}</small>
              </li>
            ))}
          </ol>
        </article>
      ))}
    </div>
  );
}
