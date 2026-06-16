import type { WorkflowRun } from "../types/domain";
import { Section } from "../components/Section";
import { WorkflowList } from "../components/WorkflowList";

type Props = {
  workflows: WorkflowRun[];
  onRefresh: () => void;
};

export function WorkflowPage({ workflows, onRefresh }: Props) {
  return (
    <Section title="Workflow 执行记录" eyebrow="Middleware" actions={<button onClick={onRefresh}>刷新记录</button>}>
      <WorkflowList workflows={workflows} />
    </Section>
  );
}
