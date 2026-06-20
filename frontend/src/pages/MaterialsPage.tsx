import { Section } from "../components/Section";
import { MarkdownContent } from "../components/MarkdownContent";

export type MaterialGeneration = "email" | "resume" | "statement" | "interview";

type Props = {
  email: string;
  resumeHighlights: string;
  statement: string;
  interview: string;
  generating: MaterialGeneration | null;
  onEmail: () => void;
  onResumeHighlights: () => void;
  onStatement: () => void;
  onInterview: () => void;
};

export function MaterialsPage({
  email,
  resumeHighlights,
  statement,
  interview,
  generating,
  onEmail,
  onResumeHighlights,
  onStatement,
  onInterview
}: Props) {
  const busy = generating !== null;

  return (
    <Section
      title="材料与面试"
      eyebrow="申请输出"
      description="基于个人画像和导师信息，生成可继续修改的申请材料与面试练习题。"
      actions={
        <>
          <button aria-busy={generating === "email"} disabled={busy} onClick={onEmail}>
            {generating === "email" ? "生成中..." : "生成导师邮件"}
          </button>
          <button
            aria-busy={generating === "resume"}
            className="secondary"
            disabled={busy}
            onClick={onResumeHighlights}
          >
            {generating === "resume" ? "生成中..." : "生成简历亮点"}
          </button>
          <button
            aria-busy={generating === "statement"}
            className="secondary"
            disabled={busy}
            onClick={onStatement}
          >
            {generating === "statement" ? "生成中..." : "生成个人陈述"}
          </button>
          <button
            aria-busy={generating === "interview"}
            className="secondary"
            disabled={busy}
            onClick={onInterview}
          >
            {generating === "interview" ? "生成中..." : "生成面试题"}
          </button>
        </>
      }
    >
      <div className="contentGrid">
        <div className="answerPanel light">
          <div className="panelHeader">
            <h3>导师邮件</h3>
            <span>联系初稿</span>
          </div>
          <MarkdownContent content={email} />
        </div>
        <div className="answerPanel light">
          <div className="panelHeader">
            <h3>简历亮点</h3>
            <span>经历包装</span>
          </div>
          <MarkdownContent content={resumeHighlights} />
        </div>
        <div className="answerPanel light">
          <div className="panelHeader">
            <h3>个人陈述</h3>
            <span>申请片段</span>
          </div>
          <MarkdownContent content={statement} />
        </div>
        <div className="answerPanel light">
          <div className="panelHeader">
            <h3>模拟面试</h3>
            <span>练习清单</span>
          </div>
          <MarkdownContent content={interview} />
        </div>
      </div>
    </Section>
  );
}
