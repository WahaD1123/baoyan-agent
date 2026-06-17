import { Section } from "../components/Section";
import type { ProfileAnalysis, SchoolRecommendation, StudentProfile } from "../types/domain";

type Props = {
  profile: StudentProfile;
  analysis: ProfileAnalysis | null;
  plan: string;
  recommendations: SchoolRecommendation[];
  timeline: string[];
  evidence: string[];
  loading: boolean;
  onGenerate: () => void;
};

const levelLabel: Record<SchoolRecommendation["level"], string> = {
  challenge: "冲刺",
  stable: "稳妥",
  safe: "保底",
};

export function PlanningPage({
  profile,
  analysis,
  plan,
  recommendations,
  timeline,
  evidence,
  loading,
  onGenerate,
}: Props) {
  return (
    <Section
      title="院校规划"
      eyebrow="第 2 步"
      description={`${profile.name} / Top ${profile.rank_percent}% / ${profile.research_interests.join("、") || "待补充方向"}`}
      actions={<button onClick={onGenerate}>{loading ? "生成中..." : "生成我的规划"}</button>}
    >
      <div className="planningHero">
        <div className="answerPanel">
          <div className="panelHeader">
            <h3>规划摘要</h3>
            <span>面向申请决策</span>
          </div>
          <pre>{plan}</pre>
        </div>
        <div className="panel accentPanel">
          <h3>核心判断</h3>
          {analysis ? (
            <ul className="plainList">
              <li>综合竞争力：{analysis.overall_score} 分</li>
              <li>学业基础：{analysis.academic_score} 分</li>
              <li>科研与方向支撑：{analysis.research_score} 分</li>
              <li>建议策略：{profile.risk_preference === "aggressive" ? "冲刺优先" : profile.risk_preference === "conservative" ? "稳妥优先" : "平衡推进"}</li>
            </ul>
          ) : (
            <p className="emptyText">先在个人背景页完成分析，这里会自动带出判断依据。</p>
          )}
          {evidence.length ? (
            <div className="recommendationSection">
              <h4>参考资料</h4>
              <div className="tagRow">
                {evidence.map((item) => (
                  <span key={item}>{item}</span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="recommendationGrid">
        {recommendations.length ? (
          recommendations.map((item) => (
            <article className="recommendationCard" key={`${item.school_name}-${item.level}`}>
              <div className="workflowTopline">
                <strong>{item.school_name}</strong>
                <span>{levelLabel[item.level]}</span>
              </div>
              <p className="muted">{item.program_name}</p>
              <div className="scoreBar">
                <span>匹配度</span>
                <strong>{item.match_score}</strong>
              </div>
              <div className="recommendationSection">
                <h4>推荐理由</h4>
                <ul className="plainList">
                  {item.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
              <div className="recommendationSection">
                <h4>风险提示</h4>
                <ul className="plainList">
                  {item.risks.map((risk) => (
                    <li key={risk}>{risk}</li>
                  ))}
                </ul>
              </div>
              <div className="recommendationSection">
                <h4>接下来做什么</h4>
                <ul className="plainList">
                  {item.todo.map((todo) => (
                    <li key={todo}>{todo}</li>
                  ))}
                </ul>
              </div>
              {item.agent_insight ? (
                <div className="recommendationSection">
                  <h4>智能建议</h4>
                  <p className="summaryText">{item.agent_insight}</p>
                </div>
              ) : null}
              {(item.materials.length || item.exam_format.length || item.deadline) ? (
                <div className="recommendationSection">
                  <h4>通知要点</h4>
                  {item.materials.length ? (
                    <>
                      <span className="muted">材料要求</span>
                      <div className="tagRow">
                        {item.materials.map((material) => (
                          <span key={material}>{material}</span>
                        ))}
                      </div>
                    </>
                  ) : null}
                  {item.exam_format.length ? (
                    <>
                      <span className="muted">考核形式</span>
                      <div className="tagRow">
                        {item.exam_format.map((exam) => (
                          <span key={exam}>{exam}</span>
                        ))}
                      </div>
                    </>
                  ) : null}
                  {item.deadline ? <p className="summaryText">截止时间：{item.deadline}</p> : null}
                </div>
              ) : null}
              {item.evidence.length ? (
                <div className="recommendationSection">
                  <h4>建议依据</h4>
                  <div className="tagRow">
                    {item.evidence.map((source) => (
                      <span key={source}>{source}</span>
                    ))}
                  </div>
                </div>
              ) : null}
            </article>
          ))
        ) : (
          <div className="panel">
            <p className="emptyText">点击“生成我的规划”后，这里会展示冲刺、稳妥、保底院校建议。</p>
          </div>
        )}
      </div>

      <div className="panel timelinePanel">
        <h3>准备节奏</h3>
        {timeline.length ? (
          <ol className="timelineList">
            {timeline.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
        ) : (
          <p className="emptyText">生成规划后，这里会展示分周准备建议。</p>
        )}
      </div>
    </Section>
  );
}
