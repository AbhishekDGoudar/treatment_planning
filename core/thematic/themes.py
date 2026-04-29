from dataclasses import dataclass, field
from typing import List


@dataclass
class Theme:
    name: str
    description: str
    keywords: List[str] = field(default_factory=list)


PREDEFINED_THEMES: List[Theme] = [
    Theme(
        name="Individualized",
        description="Plans, goals, or services tailored to the unique needs and preferences of an individual",
        keywords=["individualized", "individual plan", "person-centered", "tailored", "personalized", "unique needs"],
    ),
    Theme(
        name="Team",
        description="Team-based approaches to planning, care coordination, or service delivery",
        keywords=["team", "team-based", "multidisciplinary team", "interdisciplinary", "care team", "support team"],
    ),
    Theme(
        name="Strengths",
        description="Strengths-based approaches that focus on an individual's capabilities, assets, and potential",
        keywords=["strengths", "strengths-based", "capabilities", "assets", "abilities", "competencies"],
    ),
    Theme(
        name="Domains",
        description="References to life domains, functional areas, or developmental domains in planning",
        keywords=["domains", "life domains", "functional areas", "domain", "areas of life", "developmental domains"],
    ),
    Theme(
        name="Natural Supports",
        description="Naturally occurring, unpaid support networks in a person's community or environment",
        keywords=["natural supports", "natural support", "naturally occurring supports", "community supports"],
    ),
    Theme(
        name="Informal Supports",
        description="Informal, non-professional, non-paid support systems including friends, neighbors, volunteers",
        keywords=["informal supports", "informal support", "unpaid support", "informal network", "informal resources"],
    ),
    Theme(
        name="Family decision",
        description="Family members are explicitly named as primary or key decision makers in planning or services",
        keywords=["family decision", "family decides", "family choice", "family consent", "family as decision maker"],
    ),
    Theme(
        name="Family-driven",
        description="Processes, plans, or services that are led or driven by family members",
        keywords=["family-driven", "family driven", "family led", "family-led", "driven by family"],
    ),
    Theme(
        name="Family voice",
        description="Family input, perspectives, opinions, or participation in planning and decision-making",
        keywords=["family voice", "family input", "family perspective", "family participation", "family involvement"],
    ),
    Theme(
        name="Youth Decision",
        description="Youth or young people are explicitly named as primary or key decision makers",
        keywords=["youth decision", "youth choice", "youth consent", "youth determines", "young person decides"],
    ),
    Theme(
        name="Youth-driven",
        description="Processes, plans, or services that are led or driven by youth",
        keywords=["youth-driven", "youth driven", "youth led", "youth-led", "driven by youth"],
    ),
    Theme(
        name="Youth voice",
        description="Youth input, perspectives, opinions, or participation in planning and decision-making",
        keywords=["youth voice", "youth input", "youth perspective", "youth participation", "youth involvement"],
    ),
    Theme(
        name="Peer Support",
        description="Support provided by peers with shared lived experience, including peer specialists or mentors",
        keywords=["peer support", "peer specialist", "peer mentor", "peer-to-peer", "lived experience", "peer services"],
    ),
    Theme(
        name="Coordination/Coordinate",
        description="Coordination of services, care activities, or resources across providers or systems",
        keywords=["coordination", "coordinate", "coordinated", "care coordination", "service coordination"],
    ),
    Theme(
        name="Collaboration/Collaborative",
        description="Collaborative approaches, partnerships, or joint work across parties, agencies, or disciplines",
        keywords=["collaboration", "collaborative", "collaborate", "joint", "partnership", "working together"],
    ),
    Theme(
        name="Communication/Communicate",
        description="Practices of communication, information sharing, or exchange between parties",
        keywords=["communication", "communicate", "communicating", "information sharing", "exchange of information"],
    ),
    Theme(
        name="Child-Serving Agencies",
        description="Agencies or organizations that specifically serve children, youth, or juvenile populations",
        keywords=["child-serving", "child serving agencies", "children's agencies", "juvenile agencies", "agencies serving children"],
    ),
    Theme(
        name="Inter-Organization",
        description="Inter-organizational or inter-agency relationships, agreements, or coordination",
        keywords=["inter-organization", "inter-agency", "interagency", "between agencies", "cross-agency", "multi-agency"],
    ),
    Theme(
        name="Culture-specific",
        description="Services, approaches, or practices tailored to specific cultural groups or communities",
        keywords=["culture-specific", "culturally specific", "cultural specific", "ethnic specific", "culturally tailored"],
    ),
    Theme(
        name="Cultural Competence",
        description="Culturally competent or culturally responsive practices, training, or service delivery",
        keywords=["cultural competence", "culturally competent", "cultural sensitivity", "culturally responsive", "cultural awareness"],
    ),
]

THEME_NAMES: List[str] = [t.name for t in PREDEFINED_THEMES]
