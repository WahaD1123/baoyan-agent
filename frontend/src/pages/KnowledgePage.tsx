import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Section } from "../components/Section";
import type { Advisor, AdvisorMatchResult, DocumentItem, RetrievedChunk } from "../types/domain";

type Props = {
  documents: DocumentItem[];
  advisors: Advisor[];
  answer: string;
  isAsking: boolean;
  documentBusy: boolean;
  advisorBusy: boolean;
  advisorSearchBusy: boolean;
  matchingAdvisors: boolean;
  statusText: string;
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
    isAsking,
    documentBusy,
    advisorBusy,
    advisorSearchBusy,
    matchingAdvisors,
    statusText,
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

  function sharedDocumentType(form: HTMLFormElement, fallbackType = "notice") {
    const rootForm = form.closest(".flowPanel")?.querySelector(".inlineForm") as HTMLFormElement | null;
    const rootData = rootForm ? new FormData(rootForm) : new FormData();
    return String(rootData.get("doc_type") || fallbackType);
  }

  function setHiddenSharedFields(form: HTMLFormElement, title: string, fallbackType = "notice") {
    const titleInput = form.querySelector<HTMLInputElement>('input[name="title"]');
    const docTypeInput = form.querySelector<HTMLInputElement>('input[name="doc_type"]');
    if (titleInput) titleInput.value = title;
    if (docTypeInput) docTypeInput.value = sharedDocumentType(form, fallbackType);
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

  const [typedAnswer, setTypedAnswer] = useState(answer);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    const characters = Array.from(answer);
    let index = 0;
    setTypedAnswer("");
    setIsTyping(characters.length > 0);

    const timer = window.setInterval(() => {
      index += 1;
      setTypedAnswer(characters.slice(0, index).join(""));
      if (index >= characters.length) {
        window.clearInterval(timer);
        setIsTyping(false);
      }
    }, characters.length > 700 ? 8 : 14);

    return () => window.clearInterval(timer);
  }, [answer]);

  function documentInsight(document: DocumentItem) {
    const analysis = document.analysis ?? {};
    const requirements = Array.isArray(analysis.requirements) ? analysis.requirements.slice(0, 3).join(", ") : "";
    const dates = Array.isArray(analysis.important_dates) ? analysis.important_dates.slice(0, 2).join(", ") : "";
    if (analysis.status === "completed") {
      return ["已完成全文分析", requirements && `材料: ${requirements}`, dates && `时间: ${dates}`]
        .filter(Boolean)
        .join(" · ");
    }
    return document.keywords.slice(0, 4).join(", ") || document.content.slice(0, 54);
  }

  function renderInline(text: string): ReactNode[] {
    return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  }

  function renderMarkdown(text: string) {
    const lines = text.split(/\r?\n/);
    const nodes: ReactNode[] = [];
    let index = 0;

    while (index < lines.length) {
      const rawLine = lines[index];
      const line = rawLine.trim();
      if (!line) {
        index += 1;
        continue;
      }

      const heading = line.match(/^(#{1,4})\s+(.+)$/);
      if (heading) {
        const level = Math.min(heading[1].length, 4);
        const Tag = `h${level + 2}` as keyof JSX.IntrinsicElements;
        nodes.push(<Tag key={`heading-${index}`}>{renderInline(heading[2])}</Tag>);
        index += 1;
        continue;
      }

      if (isMarkdownTableStart(lines, index)) {
        const headers = splitTableRow(lines[index]);
        index += 2;
        const rows: string[][] = [];
        while (index < lines.length && isTableRow(lines[index])) {
          rows.push(splitTableRow(lines[index]));
          index += 1;
        }
        nodes.push(
          <div className="markdownTableWrap" key={`table-${index}`}>
            <table>
              <thead>
                <tr>
                  {headers.map((cell, cellIndex) => (
                    <th key={`head-${cellIndex}`}>{renderInline(cell)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIndex) => (
                  <tr key={`row-${rowIndex}`}>
                    {headers.map((_, cellIndex) => (
                      <td key={`cell-${rowIndex}-${cellIndex}`}>{renderInline(row[cellIndex] ?? "")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }

      if (line.startsWith(">")) {
        nodes.push(<blockquote key={`quote-${index}`}>{renderInline(line.replace(/^>\s?/, ""))}</blockquote>);
        index += 1;
        continue;
      }

      if (/^[-*]\s+/.test(line)) {
        const items: ReactNode[] = [];
        while (index < lines.length && /^[-*]\s+/.test(lines[index].trim())) {
          items.push(<li key={`ul-${index}`}>{renderInline(lines[index].trim().replace(/^[-*]\s+/, ""))}</li>);
          index += 1;
        }
        nodes.push(<ul key={`list-${index}`}>{items}</ul>);
        continue;
      }

      if (/^\d+\.\s+/.test(line)) {
        const items: ReactNode[] = [];
        while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
          items.push(<li key={`ol-${index}`}>{renderInline(lines[index].trim().replace(/^\d+\.\s+/, ""))}</li>);
          index += 1;
        }
        nodes.push(<ol key={`list-${index}`}>{items}</ol>);
        continue;
      }

      nodes.push(<p key={`p-${index}`}>{renderInline(line)}</p>);
      index += 1;
    }

    return nodes;
  }

  function isTableRow(line: string) {
    const trimmed = line.trim();
    return trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.split("|").length >= 4;
  }

  function isMarkdownTableStart(lines: string[], index: number) {
    if (!isTableRow(lines[index]) || !lines[index + 1]) {
      return false;
    }
    const separatorCells = splitTableRow(lines[index + 1]);
    return separatorCells.length > 0 && separatorCells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s/g, "")));
  }

  function splitTableRow(line: string) {
    return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
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

      <div className="operationStatus" aria-live="polite">
        <span className={documentBusy || advisorBusy || advisorSearchBusy || matchingAdvisors || isAsking ? "statusDot active" : "statusDot"} />
        <strong>当前进度</strong>
        <p>{statusText}</p>
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
              <input name="url" placeholder="这里粘贴网页链接，例如院校通知 URL / 导师主页 URL" />
              <input name="title" type="hidden" />
              <button type="submit" disabled={documentBusy}>{documentBusy ? "处理中" : "抓取资料"}</button>
            </form>

            <div className="importAlternatives">
              <div className="subSectionTitle">
                <span>网页抓不了时，用下面两种方式</span>
                <p>PDF 放左边；知乎、小红书、公众号正文复制后放右边。</p>
              </div>
              <div className="compactForms">
                <form className="stackForm" onSubmit={(event) => {
                  setHiddenSharedFields(event.currentTarget, "", "notice");
                  handlePdfSubmit(event);
                }}>
                  <div className="formHint">
                    <strong>上传通知 PDF</strong>
                    <span>使用上方选择的资料类型和资料名称。</span>
                  </div>
                  <input name="title" type="hidden" />
                  <input name="doc_type" type="hidden" />
                  <input name="file" type="file" accept="application/pdf" />
                  <button type="submit" disabled={documentBusy}>{documentBusy ? "解析中" : "上传 PDF"}</button>
                </form>

                <form className="stackForm" onSubmit={(event) => {
                  setHiddenSharedFields(event.currentTarget, "手动资料", "experience");
                  handleTextSubmit(event);
                }}>
                  <div className="formHint">
                    <strong>粘贴正文内容</strong>
                    <span>知乎、公众号、小红书等复制正文放这里。</span>
                  </div>
                  <input name="title" type="hidden" />
                  <input name="doc_type" type="hidden" />
                  <textarea name="content" placeholder="把网页正文复制到这里，例如经验贴全文、通知正文、导师介绍" rows={5} />
                  <button type="submit" disabled={documentBusy}>{documentBusy ? "分析中" : "添加文本"}</button>
                </form>
              </div>
            </div>
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
              <button type="submit" disabled={isAsking}>{isAsking ? "分析中" : "查询"}</button>
            </form>

            <div className={`answerPanel compactAnswer ${isAsking ? "isThinking" : ""}`}>
              <div className="panelHeader">
                <h3>回答结果</h3>
                <span>{isAsking ? "正在读取资料" : isTyping ? "正在生成" : "带资料来源"}</span>
              </div>
              <div className="markdownAnswer">
                {renderMarkdown(typedAnswer)}
                {(isTyping || isAsking) && <span className="typeCursor" aria-hidden="true" />}
              </div>
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
              <button type="submit" disabled={advisorBusy}>{advisorBusy ? "抓取中" : "抓取导师"}</button>
            </form>
            <form className="miniForm compactSearch" onSubmit={handleAdvisorSearch}>
              <input name="university" placeholder="学校" />
              <input name="direction" placeholder="方向" />
              <input name="keywords" placeholder="关键词" />
              <button type="submit" disabled={advisorSearchBusy}>{advisorSearchBusy ? "搜索中" : "搜索"}</button>
            </form>
            <button className="wideAction" onClick={onMatch} disabled={matchingAdvisors}>
              {matchingAdvisors ? "匹配中" : "生成导师匹配"}
            </button>
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
                  <p>{documentInsight(document)}</p>
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
                        <p>{documentInsight(document)}</p>
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
