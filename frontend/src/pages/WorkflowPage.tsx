import { Section } from "../components/Section";
import { WorkflowTraceList } from "../components/WorkflowTraceList";
import type { WorkflowRun } from "../types/domain";

type Props = {
  workflows: WorkflowRun[];
  onRefresh: () => void;
};

export function WorkflowPage({ workflows, onRefresh }: Props) {
  return (
    <Section
      title="执行记录"
      eyebrow="过程留痕"
      description="记录每次资料入库、问答、规划和导师匹配的关键步骤，方便展示系统不是只给结论。"
      actions={<button onClick={onRefresh}>刷新记录</button>}
    >
      <WorkflowTraceList workflows={workflows} />
    </Section>
  );
}
