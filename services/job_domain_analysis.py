from schemas.job_domain import JobDomainAnalysisResult, empty_job_domain_analysis
from services.domain_rules import DOMAIN_ENUMS, DOMAIN_RULES


class JobDomainAnalysisService:
    def analyze_job_domain(self, company: str, title: str, jd_text: str) -> dict:
        text = f"{company or ''}\n{title or ''}\n{jd_text or ''}".strip()
        lowered = text.lower()
        if not lowered:
            return empty_job_domain_analysis()

        scored = []
        for domain in DOMAIN_ENUMS:
            rule = DOMAIN_RULES[domain]
            business_hits = self._match(rule["business_context"], lowered)
            experience_hits = self._match(rule["required_domain_experience"], lowered)
            metric_hits = self._match(rule["core_metrics"], lowered)
            decision_hits = self._match(rule["decision_focus"], lowered)
            keyword_hits = self._match(rule["domain_keywords"], lowered)
            score = (
                len(business_hits) * 4
                + len(experience_hits) * 5
                + len(metric_hits) * 3
                + len(decision_hits) * 3
                + len(keyword_hits) * 2
            )
            diversity = sum(1 for bucket in [business_hits, experience_hits, metric_hits, decision_hits, keyword_hits] if bucket)
            score += max(0, diversity - 1) * 2
            if title and any(hit.lower() in title.lower() for hit in keyword_hits[:2]):
                score += 4
            scored.append(
                {
                    "domain": domain,
                    "score": score,
                    "business_hits": business_hits,
                    "experience_hits": experience_hits,
                    "metric_hits": metric_hits,
                    "decision_hits": decision_hits,
                    "keyword_hits": keyword_hits,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        primary = scored[0]
        secondary = scored[1] if len(scored) > 1 else None
        if primary["score"] <= 0:
            return empty_job_domain_analysis()

        confidence = self._calc_confidence(primary["score"], secondary["score"] if secondary else 0)
        secondary_domain = secondary["domain"] if secondary and secondary["score"] >= max(8, primary["score"] * 0.45) else ""

        return JobDomainAnalysisResult(
            primary_domain=primary["domain"],
            secondary_domain=secondary_domain,
            domain_confidence=confidence,
            business_context=primary["business_hits"][:4],
            required_domain_experience=primary["experience_hits"][:4],
            core_metrics=primary["metric_hits"][:4],
            decision_focus=primary["decision_hits"][:4],
            domain_keywords=primary["keyword_hits"][:6],
            reasoning=self._build_reasoning(primary, secondary_domain),
        ).to_dict()

    def _match(self, phrases: list[str], lowered: str) -> list[str]:
        hits = []
        for phrase in phrases:
            if phrase.lower() in lowered and phrase not in hits:
                hits.append(phrase)
        return hits

    def _calc_confidence(self, primary_score: int, secondary_score: int) -> int:
        margin = max(0, primary_score - secondary_score)
        confidence = 45 + min(primary_score, 12) * 3 + min(margin, 12) * 2
        return max(35, min(95, confidence))

    def _build_reasoning(self, primary: dict, secondary_domain: str) -> str:
        reasons = []
        if primary["business_hits"]:
            reasons.append(f"JD 的业务语境集中在{'、'.join(primary['business_hits'][:3])}")
        if primary["experience_hits"]:
            reasons.append(f"同时提到了{'、'.join(primary['experience_hits'][:3])}等该场景特有能力")
        if primary["metric_hits"]:
            reasons.append(f"核心指标更偏向{'、'.join(primary['metric_hits'][:2])}")
        if primary["decision_hits"]:
            reasons.append(f"决策重点落在{'、'.join(primary['decision_hits'][:2])}")
        if secondary_domain:
            reasons.append(f"另外也带有部分{secondary_domain}信号，但主场景仍以{primary['domain']}为主")
        return "；".join(reasons) or f"当前 JD 最接近 {primary['domain']}。"



def get_job_domain_analysis_service() -> JobDomainAnalysisService:
    return JobDomainAnalysisService()
