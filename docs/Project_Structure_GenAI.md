# ScholarSync Project Structure v3.3

```
scholarsync/
│
├── config/
│   ├── __init__.py
│   ├── settings.py                             # 🔒 SINGLE SOURCE OF TRUTH for all config
│   ├── models.yaml                             # Data input (model definitions)
│   └── slo.yaml                                # Data input (SLO definitions)
│
├── apps/
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── deps.py
│   │   │
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── sources.py
│   │   │   ├── chat.py
│   │   │   ├── studio.py
│   │   │   ├── notes.py
│   │   │   └── health.py
│   │   │
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py
│   │   │   ├── auth.py
│   │   │   └── common.py
│   │   │
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── sources.py
│   │       ├── chat.py
│   │       ├── studio.py
│   │       └── notes.py
│   │
│   └── worker/
│       ├── __init__.py
│       ├── celery_app.py
│       └── tasks/
│           ├── __init__.py
│           ├── pdf_task.py
│           ├── cleanup_task.py
│           └── usage_aggregation.py            # ⚠️ READ-ONLY: Only reads UsageRecord, never writes
│
├── packages/
│   │
│   └── core/
│       ├── __init__.py
│       ├── pyproject.toml
│       │
│       ├── guardrails/
│       │   ├── __init__.py
│       │   ├── cost_manager.py                 # 🔒 SINGLE SOURCE OF TRUTH for cost operations
│       │   ├── budget_enforcer.py              # Thin wrapper - delegates to CostManager
│       │   ├── input_guardian.py
│       │   └── output_moderator.py
│       │
│       ├── policies/
│       │   ├── __init__.py
│       │   └── enforcement.py
│       │
│       ├── compliance/
│       │   ├── __init__.py
│       │   ├── data_retention.py
│       │   ├── audit.py
│       │   └── privacy.py
│       │
│       ├── security/
│       │   ├── __init__.py
│       │   ├── encryption.py
│       │   ├── secrets_manager.py
│       │   └── file_validator.py
│       │
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── conversation_memory.py
│       │   ├── summarizer.py
│       │   └── context_compressor.py
│       │
│       ├── orchestrator/
│       │   ├── __init__.py
│       │   ├── task_router.py
│       │   ├── context_builder.py
│       │   ├── executor.py
│       │   └── model_selector.py
│       │
│       ├── skills/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── chat_skill.py
│       │   ├── flashcard_skill.py
│       │   ├── quiz_skill.py
│       │   ├── report_skill.py
│       │   ├── mindmap_skill.py
│       │   ├── infographic_skill.py
│       │   └── slidedeck_skill.py
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── _base.py                        # Internal base class
│       │   ├── openai_client.py                # ✅ Renamed from _openai.py
│       │   ├── gemini_client.py                # ✅ Renamed from _gemini.py
│       │   └── factory.py
│       │
│       ├── rag/
│       │   ├── __init__.py
│       │   ├── embedder.py
│       │   ├── retriever.py
│       │   ├── chunker.py
│       │   ├── vector_store.py                 # Facade - delegates to providers
│       │   │
│       │   └── vectorstores/                   # ✅ NEW: Vector DB providers
│       │       ├── __init__.py
│       │       ├── base.py                     # Abstract base for all vector stores
│       │       ├── pinecone_store.py           # Pinecone implementation
│       │       ├── pgvector_store.py           # pgvector implementation
│       │       └── qdrant_store.py             # Qdrant implementation (future)
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── s3.py
│       │   └── local.py
│       │
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   └── templates/
│       │       ├── chat.jinja2
│       │       ├── flashcard.jinja2
│       │       ├── quiz.jinja2
│       │       ├── report.jinja2
│       │       ├── mindmap.jinja2
│       │       ├── infographic.jinja2
│       │       └── slidedeck.jinja2
│       │
│       ├── database/
│       │   ├── __init__.py
│       │   ├── connection.py
│       │   │
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   ├── tenant.py
│       │   │   ├── user.py
│       │   │   ├── source.py
│       │   │   ├── chat.py
│       │   │   ├── note.py
│       │   │   ├── usage.py                    # ⚠️ Only CostManager may write UsageRecord
│       │   │   └── audit.py
│       │   │
│       │   └── migrations/
│       │       └── versions/
│       │           └── .gitkeep
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── source_service.py
│       │   ├── chat_service.py
│       │   ├── studio_service.py
│       │   └── note_service.py
│       │
│       ├── cache/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   └── decorators.py
│       │
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── exceptions.py
│       │   ├── tokens.py
│       │   ├── files.py
│       │   └── formatting.py
│       │
│       └── monitoring/
│           ├── __init__.py
│           ├── logger.py
│           ├── metrics.py
│           └── slo.py
│
├── evals/
│   ├── __init__.py
│   ├── README.md
│   │
│   ├── datasets/
│   │   ├── chat_golden.json
│   │   ├── flashcard_golden.json
│   │   ├── quiz_golden.json
│   │   ├── grounding_golden.json
│   │   └── retrieval_golden.json
│   │
│   ├── runners/
│   │   ├── __init__.py
│   │   ├── base_eval.py
│   │   ├── rag_eval.py
│   │   ├── grounding_eval.py
│   │   ├── skill_eval.py
│   │   └── latency_eval.py
│   │
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── retrieval_metrics.py
│   │   ├── generation_metrics.py
│   │   └── grounding_metrics.py
│   │
│   └── reports/
│       └── .gitkeep
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   │
│   │   ├── test_guardrails/
│   │   │   ├── __init__.py
│   │   │   ├── test_cost_manager.py
│   │   │   ├── test_budget_enforcer.py
│   │   │   ├── test_input_guardian.py
│   │   │   └── test_output_moderator.py
│   │   │
│   │   ├── test_policies/
│   │   │   ├── __init__.py
│   │   │   └── test_enforcement.py
│   │   │
│   │   ├── test_security/
│   │   │   ├── __init__.py
│   │   │   ├── test_encryption.py
│   │   │   └── test_file_validator.py
│   │   │
│   │   ├── test_memory/
│   │   │   ├── __init__.py
│   │   │   ├── test_conversation_memory.py
│   │   │   └── test_summarizer.py
│   │   │
│   │   ├── test_skills/
│   │   │   ├── __init__.py
│   │   │   ├── test_chat_skill.py
│   │   │   ├── test_flashcard_skill.py
│   │   │   └── test_quiz_skill.py
│   │   │
│   │   ├── test_orchestrator/
│   │   │   ├── __init__.py
│   │   │   ├── test_task_router.py
│   │   │   ├── test_context_builder.py
│   │   │   └── test_executor.py
│   │   │
│   │   ├── test_rag/
│   │   │   ├── __init__.py
│   │   │   ├── test_embedder.py
│   │   │   ├── test_retriever.py
│   │   │   ├── test_chunker.py
│   │   │   └── test_vectorstores/              # ✅ NEW: Tests for vector store providers
│   │   │       ├── __init__.py
│   │   │       ├── test_pinecone_store.py
│   │   │       └── test_pgvector_store.py
│   │   │
│   │   ├── test_storage/
│   │   │   ├── __init__.py
│   │   │   ├── test_s3.py
│   │   │   └── test_local.py
│   │   │
│   │   ├── test_database/
│   │   │   ├── __init__.py
│   │   │   └── test_models.py
│   │   │
│   │   └── test_llm/
│   │       ├── __init__.py
│   │       └── test_factory.py
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_chat_flow.py
│   │   ├── test_studio_flow.py
│   │   ├── test_upload_flow.py
│   │   ├── test_tenant_isolation.py
│   │   └── test_cost_enforcement.py
│   │
│   └── load/
│       ├── __init__.py
│       └── locustfile.py
│
├── scripts/
│   ├── setup.sh
│   ├── migrate.sh
│   ├── seed.py
│   ├── run_tests.sh
│   └── run_evals.sh
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── adding_skills.md
│   ├── deployment.md
│   ├── engineering_rules.md
│   ├── config_source_of_truth.md               # ✅ NEW: Config hierarchy doc
│   └── runbooks/
│       ├── llm_rate_limit.md
│       ├── database_recovery.md
│       ├── tenant_data_recovery.md
│       └── cost_spike_response.md
│
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── modules/
│   │       ├── database/
│   │       │   └── main.tf
│   │       ├── redis/
│   │       │   └── main.tf
│   │       ├── storage/
│   │       │   └── main.tf
│   │       └── kubernetes/
│   │           └── main.tf
│   │
│   ├── kubernetes/
│   │   ├── namespace.yaml
│   │   ├── api-deployment.yaml
│   │   ├── worker-deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml
│   │   ├── configmap.yaml                      # Maps to env vars → settings.py
│   │   ├── secrets.yaml                        # External secrets / K8s secrets
│   │   └── hpa.yaml
│   │
│   └── helm/
│       └── scholarsync/
│           ├── Chart.yaml
│           ├── values.yaml                     # Maps to env vars → settings.py
│           └── templates/
│               └── .gitkeep
│
├── .github/
│   └── workflows/
│       ├── test.yml
│       ├── lint.yml
│       ├── security.yml
│       ├── evals.yml
│       ├── enforce.yml
│       └── deploy.yml
│
├── .env.example                                # ✅ ONLY this committed to repo
├── .gitignore                                  # ✅ Must exclude .env* (except .env.example)
├── .dockerignore
├── Dockerfile.api
├── Dockerfile.worker
├── docker-compose.yml
├── docker-compose.test.yml
├── pyproject.toml
├── alembic.ini
├── Makefile
└── README.md
```
