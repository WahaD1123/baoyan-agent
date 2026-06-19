import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  content: string;
};

export function MarkdownContent({ content }: Props) {
  return (
    <div className="markdownBody">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
