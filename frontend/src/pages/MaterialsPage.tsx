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
      title="材料生成与模拟面试"
      eyebrow="Member C"
      actions={
        <>
          <button onClick={onEmail}>生成导师邮件</button>
          <button className="secondary" onClick={onInterview}>生成面试题</button>
        </>
      }
    >
      <div className="split">
        <div>
          <h3>导师邮件</h3>
          <pre className="resultBox">{email}</pre>
        </div>
        <div>
          <h3>模拟面试</h3>
          <pre className="resultBox">{interview}</pre>
        </div>
      </div>
    </Section>
  );
}
