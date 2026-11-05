FULL_STACK_QUESTIONS = [
    # -------------------------
    # Frontend
    # -------------------------

    {
        "category": "Frontend",
        "question_text": "What is the difference between client-side rendering and server-side rendering?",
    },
    {
        "category": "Frontend",
        "question_text": "Explain how the DOM works and how JavaScript interacts with it.",
    },
    {
        "category": "Frontend",
        "question_text": "What is the difference between state and props in a frontend framework such as React?",
    },
    {
        "category": "Frontend",
        "question_text": "What causes unnecessary re-renders in a React application, and how would you reduce them?",
    },
    {
        "category": "Frontend",
        "question_text": "What is event bubbling in JavaScript, and when would event delegation be useful?",
    },
    {
        "category": "Frontend",
        "question_text": "Explain the difference between synchronous and asynchronous JavaScript.",
    },
    {
        "category": "Frontend",
        "question_text": "What are promises and async/await, and how do they simplify asynchronous code?",
    },
    {
        "category": "Frontend",
        "question_text": "How would you improve the performance of a web page containing many large images and JavaScript bundles?",
    },
    {
        "category": "Frontend",
        "question_text": "What is responsive web design, and how would you approach building a responsive application?",
    },
    {
        "category": "Frontend",
        "question_text": "How would you manage form validation on the frontend while keeping the application secure?",
    },

    # -------------------------
    # Backend
    # -------------------------

    {
        "category": "Backend",
        "question_text": "What responsibilities typically belong to the backend of a web application?",
    },
    {
        "category": "Backend",
        "question_text": "What is middleware, and where would you use it in a backend application?",
    },
    {
        "category": "Backend",
        "question_text": "Explain the difference between synchronous and asynchronous request handling on a backend.",
    },
    {
        "category": "Backend",
        "question_text": "What is dependency injection, and why can it be useful in backend applications?",
    },
    {
        "category": "Backend",
        "question_text": "How would you structure a backend application so that business logic does not become tightly coupled to API routes?",
    },
    {
        "category": "Backend",
        "question_text": "What is the purpose of environment variables in a backend application?",
    },
    {
        "category": "Backend",
        "question_text": "How would you handle unexpected exceptions in a production backend?",
    },
    {
        "category": "Backend",
        "question_text": "What is connection pooling, and why is it important when an application communicates with a relational database?",
    },
    {
        "category": "Backend",
        "question_text": "How would you design a backend endpoint that needs to process a large amount of data without blocking other requests?",
    },
    {
        "category": "Backend",
        "question_text": "What are common causes of slow backend API responses, and how would you investigate them?",
    },

    # -------------------------
    # Databases
    # -------------------------

    {
        "category": "Databases",
        "question_text": "What is the difference between a relational database and a NoSQL database?",
    },
    {
        "category": "Databases",
        "question_text": "What is database normalization, and what problem does it solve?",
    },
    {
        "category": "Databases",
        "question_text": "What is a database index, and how does it improve query performance?",
    },
    {
        "category": "Databases",
        "question_text": "Can adding too many indexes hurt database performance? Explain why.",
    },
    {
        "category": "Databases",
        "question_text": "Explain the difference between a primary key and a foreign key.",
    },
    {
        "category": "Databases",
        "question_text": "What is a database transaction, and what properties are described by ACID?",
    },
    {
        "category": "Databases",
        "question_text": "How would you investigate a SQL query that suddenly became much slower?",
    },
    {
        "category": "Databases",
        "question_text": "What is the difference between INNER JOIN and LEFT JOIN, and when would you use each?",
    },

    # -------------------------
    # APIs & Authentication
    # -------------------------

    {
        "category": "APIs",
        "question_text": "What is REST, and what principles are commonly associated with RESTful APIs?",
    },
    {
        "category": "APIs",
        "question_text": "What is the difference between GET, POST, PUT, PATCH, and DELETE?",
    },
    {
        "category": "APIs",
        "question_text": "What HTTP status codes would you use for a successful request, a validation error, an unauthorized request, and a missing resource?",
    },
    {
        "category": "APIs",
        "question_text": "What is idempotency in an API, and why does it matter?",
    },
    {
        "category": "APIs",
        "question_text": "How would you design pagination for an API returning thousands of records?",
    },
    {
        "category": "Authentication",
        "question_text": "What is the difference between authentication and authorization?",
    },
    {
        "category": "Authentication",
        "question_text": "Explain how JWT-based authentication works and describe one limitation of using JWTs.",
    },

    # -------------------------
    # Testing & Debugging
    # -------------------------

    {
        "category": "Testing",
        "question_text": "What is the difference between unit testing, integration testing, and end-to-end testing?",
    },
    {
        "category": "Testing",
        "question_text": "What makes a good unit test?",
    },
    {
        "category": "Testing",
        "question_text": "How would you test an API endpoint that creates a new user?",
    },
    {
        "category": "Testing",
        "question_text": "A production API occasionally returns a 500 error, but you cannot reproduce it locally. How would you investigate the problem?",
    },
    {
        "category": "Testing",
        "question_text": "What is mocking, and when can excessive mocking make tests less useful?",
    },

    # -------------------------
    # Git & Deployment
    # -------------------------

    {
        "category": "Git",
        "question_text": "What is the difference between git merge and git rebase?",
    },
    {
        "category": "Git",
        "question_text": "How would you resolve a merge conflict in Git?",
    },
    {
        "category": "Deployment",
        "question_text": "What is CI/CD, and what problem does it solve?",
    },
    {
        "category": "Deployment",
        "question_text": "Why would you use Docker for deploying a full-stack application?",
    },
    {
        "category": "Deployment",
        "question_text": "What steps would you take before deploying a backend application to production?",
    },

    # -------------------------
    # System Design / Practical
    # -------------------------

    {
        "category": "System Design",
        "question_text": "How would you design a URL shortening service at a high level?",
    },
    {
        "category": "System Design",
        "question_text": "How would you design a basic file-upload service that stores user files safely?",
    },
    {
        "category": "System Design",
        "question_text": "Your web application suddenly receives ten times its normal traffic. What parts of the system would you examine first?",
    },
    {
        "category": "System Design",
        "question_text": "When would you introduce a caching layer into a web application, and what problems can caching create?",
    },
    {
        "category": "System Design",
        "question_text": "How would you design a full-stack application so that a slow third-party API does not make the entire application unusable?",
    },
]

if __name__ == "__main__":
    print(f"Total questions: {len(FULL_STACK_QUESTIONS)}")