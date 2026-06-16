import type { FormEvent } from "react";
import { Section } from "../components/Section";
import type { Advisor, AdvisorMatchResult, DocumentItem, RetrievedChunk } from "../types/domain";

type Props = {
  documents: DocumentItem[];
  advisors: Advisor[];
  answer: string;
  chunks: RetrievedChunk[];
  matches: AdvisorMatchResult[];
  onAddText: (payload: { title: string; doc_type: string; content: string; source: string }) => void;
  onAddUrl: (payload: { title?: string; doc_type: string; url: string }) => void;
  onUploadPdf: (file: File, docType: string, title: string) => void;
  onAddAdvisorUrl: (url: string, title?: string) => void;
  onSearchAdvisor: (payload: { university: string; direction: string; keywords: string[] }) => void;
  onAsk: (question: string) => void;
  onMatch: () => void;
};

const typeLabels: Record<string, string> = {
  notice: "院校通知",
  experience: "经验贴",
  advisor: "导师主页",
  resume: "简历材料",
  other: "其他资料"
};

export function KnowledgePage(props: Props) {
  const {
    documents,
    advisors,
    answer,
    chunks,
    matches,
    onAddText,
    onAddUrl,
    onUploadPdf,
    onAddAdvisorUrl,
    onSearchAdvisor,
    onAsk,
    onMatch
  } = props;

  function handleUrlSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const url = String(form.get("url") || "").trim();
    if (!url) return;
    onAddUrl({
      url,
      title: String(form.get("title") || ""),
      doc_type: String(form.get("doc_type") || "notice")
    });
  }

  function handlePdfSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    if (file instanceof File && file.size > 0) {
      onUploadPdf(file, String(form.get("doc_type") || "notice"), String(form.get("title") || file.name));
    }
  }

  function handleTextSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const content = String(form.get("content") || "").trim();
    if (!content) return;
    onAddText({
      title: String(form.get("title") || "手动资料"),
      doc_type: String(form.get("doc_type") || "experience"),
      content,
      source: "manual"
    });
    event.currentTarget.reset();
  }

  function handleAdvisorUrlSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const url = String(form.get("advisor_url") || "").trim();
    if (!url) return;
    onAddAdvisorUrl(url, String(form.get("advisor_title") || ""));
  }

  function handleAdvisorSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSearchAdvisor({
      university: String(form.get("university") || ""),
      direction: String(form.get("direction") || ""),
      keywords: String(form.get("keywords") || "")
        .split(/[,\s]+/)
        .filter(Boolean)
    });
  }

  function handleQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onAsk(String(form.get("question") || "这个夏令营需要哪些材料？"));
  }

  return (
    <Section title="资料库与导师匹配" eyebrow="成员 B 模块">
      <div className="flowSteps">
        <article>
          <span>1</span>
          <strong>收集资料</strong>
          <p>通知、PDF、经验贴先入库。</p>
        </article>
        <article>
          <span>2</span>
          <strong>提问核对</strong>
          <p>围绕材料、时间和考核快速问。</p>
        </article>
        <article>
          <span>3</span>
          <strong>匹配导师</strong>
          <p>补充导师主页后生成推荐。</p>
        </article>
      </div>

      <div className="knowledgeFlow">
        <div className="mainFlow">
          <div className="panel flowPanel">
            <div className="panelHeader">
              <div>
                <span className="stepLabel">第一步</span>
                <h3>添加申请资料</h3>
              </div>
              <span>{documents.length} 份</span>
            </div>
            <form className="inlineForm" onSubmit={handleUrlSubmit}>
              <select name="doc_type" defaultValue="notice" aria-label="资料类型">
                <option value="notice">院校通知</option>
                <option value="experience">经验贴</option>
                <option value="advisor">导师主页</option>
                <option value="other">其他资料</option>
              </select>
              <input name="url" placeholder="粘贴院校通知、经验贴或导师主页 URL" />
              <input name="title" placeholder="标题，可不填" />
              <button type="submit">抓取资料</button>
            </form>

            <details className="softDetails">
              <summary>上传 PDF 或粘贴文本</summary>
              <div className="compactForms">
                <form className="stackForm" onSubmit={handlePdfSubmit}>
                  <input name="title" placeholder="PDF 标题，可不填" />
                  <select name="doc_type" defaultValue="notice">
                    <option value="notice">院校通知</option>
                    <option value="experience">经验贴</option>
                    <option value="resume">简历材料</option>
                  </select>
                  <input name="file" type="file" accept="application/pdf" />
                  <button type="submit">上传 PDF</button>
                </form>

                <form className="stackForm" onSubmit={handleTextSubmit}>
                  <input name="title" placeholder="文本资料标题" />
                  <select name="doc_type" defaultValue="experience">
                    <option value="notice">院校通知</option>
                    <option value="experience">经验贴</option>
                    <option value="advisor">导师资料</option>
                    <option value="other">其他资料</option>
                  </select>
                  <textarea name="content" placeholder="粘贴通知、经验贴或导师资料" rows={5} />
                  <button type="submit">添加文本</button>
                </form>
              </div>
            </details>
          </div>

          <div className="panel flowPanel">
            <div className="panelHeader">
              <div>
                <span className="stepLabel">第二步</span>
                <h3>基于资料提问</h3>
              </div>
              <span>{chunks.length} 条引用</span>
            </div>
            <form className="queryBar" onSubmit={handleQuestion}>
              <input name="question" placeholder="例如：这个夏令营需要哪些材料？报名什么时候截止？" />
              <button type="submit">查询</button>
            </form>

            <div className="answerPanel compactAnswer">
              <div className="panelHeader">
                <h3>回答结果</h3>
                <span>带资料来源</span>
              </div>
              <pre>{answer}</pre>
            </div>

            <details className="dropdownList evidenceDropdown">
              <summary>查看引用片段 {chunks.length} 条</summary>
              <div className="compactList denseList">
                {chunks.length ? chunks.slice(0, 5).map((chunk) => (
                  <article key={chunk.chunk_id}>
                    <strong>{chunk.document_title}</strong>
                    <span>相关度 {chunk.score} / {chunk.hit_reason}</span>
                    <p>{chunk.text}</p>
                  </article>
                )) : <p className="emptyText">运行问答后，这里会展示系统引用过的原始资料片段。</p>}
              </div>
            </details>
          </div>
        </div>

        <aside className="sideFlow">
          <div className="panel accentPanel advisorActionPanel">
            <div className="panelHeader">
              <div>
                <span className="stepLabel">第三步</span>
                <h3>导师资料与匹配</h3>
              </div>
              <span>{advisors.length} 位</span>
            </div>
            <form className="miniForm" onSubmit={handleAdvisorUrlSubmit}>
              <input name="advisor_url" placeholder="导师主页 URL" />
              <input name="advisor_title" placeholder="标题，可不填" />
              <button type="submit">抓取导师</button>
            </form>
            <form className="miniForm compactSearch" onSubmit={handleAdvisorSearch}>
              <input name="university" placeholder="学校" />
              <input name="direction" placeholder="方向" />
              <input name="keywords" placeholder="关键词" />
              <button type="submit">搜索</button>
            </form>
            <button className="wideAction" onClick={onMatch}>生成导师匹配</button>
          </div>

          <div className="panel">
            <div className="panelHeader">
              <h3>匹配结果</h3>
              <span>{matches.length} 条</span>
            </div>
            <div className="compactList denseList">
              {matches.length ? matches.slice(0, 3).map((match) => (
                <article key={match.advisor.id}>
                  <strong>{match.advisor.name} / {match.score}</strong>
                  <span>{match.reasons.join("；")}</span>
                  <p>{match.contact_suggestion}</p>
                </article>
              )) : <p className="emptyText">点击“生成导师匹配”后，这里会展示推荐排序、理由和联系建议。</p>}
            </div>
          </div>

          <div className="panel">
            <div className="panelHeader">
              <h3>已收集资料</h3>
              <span>{documents.length} 份</span>
            </div>
            <div className="compactList denseList">
              {documents.slice(0, 2).map((document) => (
                <article key={document.id}>
                  <strong>{document.title}</strong>
                  <span>{typeLabels[document.doc_type] ?? document.doc_type} / {document.source_type}</span>
                  <p>{document.keywords.slice(0, 4).join(", ") || document.content.slice(0, 54)}</p>
                </article>
              ))}
              {documents.length > 2 ? (
                <details className="dropdownList">
                  <summary>查看其余 {documents.length - 2} 份资料</summary>
                  <div className="compactList denseList">
                    {documents.slice(2, 8).map((document) => (
                      <article key={document.id}>
                        <strong>{document.title}</strong>
                        <span>{typeLabels[document.doc_type] ?? document.doc_type} / {document.source_type}</span>
                        <p>{document.keywords.slice(0, 4).join(", ") || document.content.slice(0, 54)}</p>
                      </article>
                    ))}
                  </div>
                </details>
              ) : null}
            </div>
          </div>

          <div className="panel">
            <div className="panelHeader">
              <h3>导师库</h3>
              <span>{advisors.length} 位</span>
            </div>
            <div className="compactList denseList">
              {advisors.slice(0, 2).map((advisor) => (
                <article key={advisor.id}>
                  <strong>{advisor.name}</strong>
                  <span>{advisor.university}</span>
                  <p>{advisor.research_areas.join(", ") || advisor.summary}</p>
                </article>
              ))}
              {advisors.length > 2 ? (
                <details className="dropdownList">
                  <summary>查看其余 {advisors.length - 2} 位导师</summary>
                  <div className="compactList denseList">
                    {advisors.slice(2, 8).map((advisor) => (
                      <article key={advisor.id}>
                        <strong>{advisor.name}</strong>
                        <span>{advisor.university}</span>
                        <p>{advisor.research_areas.join(", ") || advisor.summary}</p>
                      </article>
                    ))}
                  </div>
                </details>
              ) : null}
            </div>
          </div>
        </aside>
      </div>
    </Section>
  );
}
