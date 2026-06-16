import { Section } from "../components/Section";

type Props = {
  email: string;
  interview: string;
  onEmail: () => void;
  onInterview: () => void;
};

export function MaterialsPage({ email, interview, onEmail, onInterview }: Props) {
  return (
    <Section
      title="材料与面试"
      eyebrow="申请输出"
      description="基于个人画像和导师信息，生成可继续修改的联系邮件与面试练习题。"
      actions={
        <>
          <button onClick={onEmail}>生成导师邮件</button>
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
          <pre>{email}</pre>
        </div>
        <div className="answerPanel light">
          <div className="panelHeader">
            <h3>模拟面试</h3>
            <span>练习清单</span>
          </div>
          <pre>{interview}</pre>
        </div>
      </div>
    </Section>
  );
}
