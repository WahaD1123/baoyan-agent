import type { Advisor, DocumentItem } from "../types/domain";
import { Section } from "../components/Section";

type Props = {
  documents: DocumentItem[];
  advisors: Advisor[];
  answer: string;
  onAsk: () => void;
  onMatch: () => void;
};

export function KnowledgePage({ documents, advisors, answer, onAsk, onMatch }: Props) {
  return (
    <Section
      title="资料知识库与导师匹配"
      eyebrow="Member B"
      actions={
        <>
          <button onClick={onAsk}>运行 RAG 问答</button>
          <button className="secondary" onClick={onMatch}>匹配导师</button>
        </>
      }
    >
      <div className="split">
        <div>
          <h3>资料库</h3>
          <div className="itemList">
            {documents.map((document) => (
              <article key={document.id}>
                <strong>{document.title}</strong>
                <span>{document.doc_type} / {document.source}</span>
                <p>{document.content}</p>
              </article>
            ))}
          </div>
        </div>
        <div>
          <h3>导师候选</h3>
          <div className="itemList">
            {advisors.map((advisor) => (
              <article key={advisor.id}>
                <strong>{advisor.name} - {advisor.university}</strong>
                <span>{advisor.research_areas.join(", ")}</span>
                <p>{advisor.summary}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
      <pre className="resultBox">{answer}</pre>
    </Section>
  );
}
