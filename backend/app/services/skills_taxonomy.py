SKILLS_TAXONOMY: dict[str, tuple[str, ...]] = {
    "javascript": ("javascript", "ecmascript", "js"),
    "typescript": ("typescript", "ts"),
    "react": ("react", "react.js", "reactjs"),
    "next.js": ("next.js", "nextjs"),
    "node.js": ("node.js", "nodejs", "node"),
    "html": ("html", "html5"),
    "css": ("css", "css3"),
    "tailwind css": ("tailwind", "tailwind css"),
    "sql": ("sql",),
    "postgresql": ("postgresql", "postgres"),
    "mysql": ("mysql",),
    "mongodb": ("mongodb", "mongo"),
    "rest api": ("rest api", "restful api", "restful", "restful service", "rest api"),
    "graphql": ("graphql",),
    "git": ("git", "github", "gitlab"),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "aws": ("aws", "amazon web services"),
    "azure": ("azure",),
    "gcp": ("gcp", "google cloud platform"),
    "python": ("python",),
    "java": ("java",),
    "c++": ("c++", "cpp"),
    "c#": ("c#", "c sharp"),
    ".net": (".net", "dotnet"),
    "fastapi": ("fastapi",),
    "django": ("django",),
    "flask": ("flask",),
    "spring boot": ("spring boot",),
    "machine learning": ("machine learning", "ml", "ml model"),
    "deep learning": ("deep learning",),
    "tensorflow": ("tensorflow",),
    "pytorch": ("pytorch",),
    "scikit-learn": ("scikit-learn", "sklearn"),
    "pandas": ("pandas",),
    "numpy": ("numpy",),
    "data analysis": ("data analysis", "data analytics"),
    "data visualization": (
        "data visualization",
        "data viz",
        "visualization",
        "visualisation",
        "dashboard",
        "dashboarding",
    ),
    "tableau": ("tableau",),
    "power bi": ("power bi", "powerbi"),
    "excel": ("excel", "microsoft excel"),
    "statistics": ("statistics", "statistical analysis"),
    "etl": ("etl",),
    "airflow": ("airflow", "apache airflow"),
    "spark": ("spark", "apache spark"),
    "linux": ("linux",),
    "bash": ("bash", "shell scripting"),
    "ci/cd": (
        "ci/cd",
        "ci cd",
        "continuous integration",
        "continuous delivery",
        "github actions",
    ),
    "terraform": ("terraform",),
    "ansible": ("ansible",),
    "jenkins": ("jenkins",),
    "prometheus": ("prometheus",),
    "grafana": ("grafana",),
    "figma": ("figma",),
    "adobe xd": ("adobe xd",),
    "wireframing": ("wireframing", "wireframe"),
    "prototyping": ("prototyping", "prototypes"),
    "user research": ("user research", "user experience research"),
    "usability testing": ("usability testing",),
    "interaction design": ("interaction design",),
    "visual design": ("visual design",),
    "accessibility": ("accessibility", "wcag"),
    "agile": ("agile",),
    "scrum": ("scrum",),
    "communication": ("communication",),
    "project management": ("project management",),
    "problem solving": ("problem solving", "problem-solving"),
}


def find_skills(text: str) -> list[str]:
    import re

    def normalize(value: str) -> str:
        normalized = value.casefold().replace("-", " ").replace("_", " ").replace("/", " ")
        return " ".join(normalized.split())

    normalized_text = normalize(text)
    found = []
    for canonical, aliases in SKILLS_TAXONOMY.items():
        if any(
            re.search(
                rf"(?<!\w){re.escape(normalize(alias))}(?:s|es)?(?!\w)",
                normalized_text,
            )
            for alias in aliases
        ):
            found.append(canonical)
    return found
