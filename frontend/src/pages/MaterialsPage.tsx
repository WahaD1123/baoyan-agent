import { Section } from "../components/Section";
import { MarkdownContent } from "../components/MarkdownContent";

type Props = {
  email: string;
  resumeHighlights: string;
  statement: string;
  interview: string;
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
  onEmail,
  onResumeHighlights,
  onStatement,
  onInterview
}: Props) {
  return (
    <Section
      title="材料与面试"
      eyebrow="申请输出"
      description="基于个人画像和导师信息，生成可继续修改的申请材料与面试练习题。"
      actions={
        <>
          <button onClick={onEmail}>生成导师邮件</button>
          <button className="secondary" onClick={onResumeHighlights}>生成简历亮点</button>
          <button className="secondary" onClick={onStatement}>生成个人陈述</button>
          <button className="secondary" onClick={onInterview}>生成面试题</button>
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
