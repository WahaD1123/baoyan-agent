import type { ReactNode } from "react";

type Props = {
  title: string;
  eyebrow?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function Section({ title, eyebrow, description, actions, children }: Props) {
  return (
    <section className="section">
      <div className="sectionHeader">
        <div>
          {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
          <h2>{title}</h2>
          {description ? <p className="sectionDescription">{description}</p> : null}
        </div>
        {actions ? <div className="sectionActions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}
