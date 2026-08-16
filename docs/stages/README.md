# Stage Documentation

## Active stages

Only files under [`active/`](active/) are executable current tasks.

Current active stage files:

- none.

Stage 7D.0 local self-message preservation during Telegram cleanup is recorded
in [`reports/STAGE_7D_0_PRESERVE_LOCAL_SELF_MESSAGES_ON_CLEAN_REPORT.md`](reports/STAGE_7D_0_PRESERVE_LOCAL_SELF_MESSAGES_ON_CLEAN_REPORT.md).

Stage completion policy: any stage that changes code or tests must run the
same completion gate as `.github/workflows/ci.yml`. When CI runs `make verify`,
local/stage completion must run `make verify`; focused checks do not replace
it. Docs-only stages are exempt when they do not change code/tests. If tooling
or environment prevents `make verify`, the stage must remain incomplete or
blocked, not complete.

Stage 6A CLI runtime boundary extraction is complete. The older
release-preparation summary below is historical index context, not active task
authorization.

Stage 6G.0 compatibility surface baseline is recorded in [`reports/STAGE_6G_0_COMPATIBILITY_SURFACE_BASELINE_REPORT.md`](reports/STAGE_6G_0_COMPATIBILITY_SURFACE_BASELINE_REPORT.md).
Stage 6G.1 internal import convergence is recorded in [`reports/STAGE_6G_1_INTERNAL_IMPORT_CONVERGENCE_REPORT.md`](reports/STAGE_6G_1_INTERNAL_IMPORT_CONVERGENCE_REPORT.md).
Stage 6G.2 SQLite write path aggregator shrink is recorded in [`reports/STAGE_6G_2_SQLITE_WRITE_PATH_AGGREGATOR_SHRINK_REPORT.md`](reports/STAGE_6G_2_SQLITE_WRITE_PATH_AGGREGATOR_SHRINK_REPORT.md).
Stage 6H.0 package changelog version history cleanup is recorded in [`reports/STAGE_6H_0_PACKAGE_CHANGELOG_VERSION_HISTORY_CLEANUP_REPORT.md`](reports/STAGE_6H_0_PACKAGE_CHANGELOG_VERSION_HISTORY_CLEANUP_REPORT.md).
Stage 7A.0 test infrastructure baseline and hardening plan is recorded in [`reports/STAGE_7A_0_TEST_INFRASTRUCTURE_BASELINE_AND_HARDENING_PLAN_REPORT.md`](reports/STAGE_7A_0_TEST_INFRASTRUCTURE_BASELINE_AND_HARDENING_PLAN_REPORT.md).
Stage 7A.1 pytest authority and CI gate alignment is recorded in [`reports/STAGE_7A_1_PYTEST_AUTHORITY_AND_CI_GATE_ALIGNMENT_REPORT.md`](reports/STAGE_7A_1_PYTEST_AUTHORITY_AND_CI_GATE_ALIGNMENT_REPORT.md).
Stage 7A.2 fixture contract snapshot gate is recorded in [`reports/STAGE_7A_2_FIXTURE_CONTRACT_SNAPSHOT_GATE_REPORT.md`](reports/STAGE_7A_2_FIXTURE_CONTRACT_SNAPSHOT_GATE_REPORT.md).
Stage 7A.3 coverage and typecheck gate precheck is recorded in [`reports/STAGE_7A_3_COVERAGE_AND_TYPECHECK_GATE_PRECHECK_REPORT.md`](reports/STAGE_7A_3_COVERAGE_AND_TYPECHECK_GATE_PRECHECK_REPORT.md).
Stage 7B.0 VPS Docker Compose deployment wrapper is recorded in [`reports/STAGE_7B_0_VPS_DOCKER_COMPOSE_DEPLOYMENT_REPORT.md`](reports/STAGE_7B_0_VPS_DOCKER_COMPOSE_DEPLOYMENT_REPORT.md).
Stage 7B.1 VPS state sync safety correction is recorded in [`reports/STAGE_7B_1_VPS_STATE_SYNC_SAFETY_CORRECTION_REPORT.md`](reports/STAGE_7B_1_VPS_STATE_SYNC_SAFETY_CORRECTION_REPORT.md).
Stage 7B.2 VPS systemd scheduler is recorded in [`reports/STAGE_7B_2_VPS_SYSTEMD_SCHEDULER_REPORT.md`](reports/STAGE_7B_2_VPS_SYSTEMD_SCHEDULER_REPORT.md).
Stage 6B.0 direct export failure exit code is recorded in [`reports/STAGE_6B_0_DIRECT_EXPORT_FAILURE_EXIT_CODE_REPORT.md`](reports/STAGE_6B_0_DIRECT_EXPORT_FAILURE_EXIT_CODE_REPORT.md).
Stage 6B.1 direct PM archive failure exit code is recorded in [`reports/STAGE_6B_1_DIRECT_PM_ARCHIVE_FAILURE_EXIT_CODE_REPORT.md`](reports/STAGE_6B_1_DIRECT_PM_ARCHIVE_FAILURE_EXIT_CODE_REPORT.md).
Stage 6C.0 SQLite writer flush failure diagnosis is recorded in [`reports/STAGE_6C_0_SQLITE_WRITER_FLUSH_FAILURE_DIAGNOSIS_REPORT.md`](reports/STAGE_6C_0_SQLITE_WRITER_FLUSH_FAILURE_DIAGNOSIS_REPORT.md).
Stage 6C.1 SQLite writer failed batch queue accounting is recorded in [`reports/STAGE_6C_1_SQLITE_WRITER_FAILED_BATCH_QUEUE_ACCOUNTING_REPORT.md`](reports/STAGE_6C_1_SQLITE_WRITER_FAILED_BATCH_QUEUE_ACCOUNTING_REPORT.md).
Stage 6C.2 SQLite writer reliability changelog and lifecycle cleanup is recorded in [`reports/STAGE_6C_2_SQLITE_WRITER_RELIABILITY_CHANGELOG_LIFECYCLE_REPORT.md`](reports/STAGE_6C_2_SQLITE_WRITER_RELIABILITY_CHANGELOG_LIFECYCLE_REPORT.md).
Stage 6D.0 FloodWait bounded retry is recorded in [`reports/STAGE_6D_0_FLOODWAIT_BOUNDED_RETRY_REPORT.md`](reports/STAGE_6D_0_FLOODWAIT_BOUNDED_RETRY_REPORT.md).
Stage 6D.1 throttler rate recovery is recorded in [`reports/STAGE_6D_1_THROTTLER_RATE_RECOVERY_REPORT.md`](reports/STAGE_6D_1_THROTTLER_RATE_RECOVERY_REPORT.md).
Stage 6E.0 CI gate alignment and Ruff format guardrails are recorded in [`reports/STAGE_6E_0_CI_GATE_ALIGNMENT_AND_RUFF_FORMAT_GUARDRAILS_REPORT.md`](reports/STAGE_6E_0_CI_GATE_ALIGNMENT_AND_RUFF_FORMAT_GUARDRAILS_REPORT.md).
Stage 6F.0 SQLite schema startup guardrails are recorded in [`reports/STAGE_6F_0_SQLITE_SCHEMA_STARTUP_GUARDRAILS_REPORT.md`](reports/STAGE_6F_0_SQLITE_SCHEMA_STARTUP_GUARDRAILS_REPORT.md).
Stage 6F.1 SQLite schema startup path split is recorded in [`reports/STAGE_6F_1_SQLITE_SCHEMA_STARTUP_PATH_SPLIT_REPORT.md`](reports/STAGE_6F_1_SQLITE_SCHEMA_STARTUP_PATH_SPLIT_REPORT.md).
Stage 6F.2 SQLite migration registry decision is recorded in [`reports/STAGE_6F_2_SQLITE_MIGRATION_REGISTRY_DECISION_REPORT.md`](reports/STAGE_6F_2_SQLITE_MIGRATION_REGISTRY_DECISION_REPORT.md).
Stage 6A.0 CLI runtime boundary precheck is recorded in [`reports/STAGE_6A_0_CLI_RUNTIME_BOUNDARY_PRECHECK_REPORT.md`](reports/STAGE_6A_0_CLI_RUNTIME_BOUNDARY_PRECHECK_REPORT.md).
Stage 6A.1 application runtime boundary guardrails are recorded in [`reports/STAGE_6A_1_APPLICATION_RUNTIME_BOUNDARY_GUARDRAILS_REPORT.md`](reports/STAGE_6A_1_APPLICATION_RUNTIME_BOUNDARY_GUARDRAILS_REPORT.md).
Stage 6A.2 runtime resource factory extraction is recorded in [`reports/STAGE_6A_2_RUNTIME_RESOURCE_FACTORY_EXTRACTION_REPORT.md`](reports/STAGE_6A_2_RUNTIME_RESOURCE_FACTORY_EXTRACTION_REPORT.md).
Stage 6A.3 service bundle factory extraction is recorded in [`reports/STAGE_6A_3_SERVICE_BUNDLE_FACTORY_EXTRACTION_REPORT.md`](reports/STAGE_6A_3_SERVICE_BUNDLE_FACTORY_EXTRACTION_REPORT.md).
Stage 6A.4 runtime session lifecycle extraction is recorded in [`reports/STAGE_6A_4_RUNTIME_SESSION_LIFECYCLE_EXTRACTION_REPORT.md`](reports/STAGE_6A_4_RUNTIME_SESSION_LIFECYCLE_EXTRACTION_REPORT.md).
Stage 6A.5 CLIContext adapter shrink is recorded in [`reports/STAGE_6A_5_CLI_CONTEXT_ADAPTER_SHRINK_REPORT.md`](reports/STAGE_6A_5_CLI_CONTEXT_ADAPTER_SHRINK_REPORT.md).
Stage 6A.6 headless runtime contract is recorded in [`reports/STAGE_6A_6_HEADLESS_RUNTIME_CONTRACT_REPORT.md`](reports/STAGE_6A_6_HEADLESS_RUNTIME_CONTRACT_REPORT.md).

Release-preparation stages were executed sequentially. Stage 5Q and Stage 5R
are split into atomic sub-stages. Stages 5U.2-5U.4 separate license decision,
metadata application, and package verification. Stage 5V first decides that
`v0.1.0-rc1` is ineligible because it predates final MIT metadata; Stages
5U.5-5U.8 then plan, create, and verify `v0.1.0-rc2`; Stage 5V.1 verifies
TestPyPI readiness, Stage 5V.2 prepares an OIDC-only GitHub Actions TestPyPI
workflow, and Stage 5V.3 registers its exact pending publisher without
publishing. Stage 5V.4 performs and verifies exactly one controlled workflow
publish of exact tag `v0.1.0-rc2` to TestPyPI. Stage 5V.5 verifies public
TestPyPI installation and help-only CLI smoke. Stage 5W prepares evidence and
decides the stable-tag and Trusted Publishing requirements for main PyPI
without publishing. Stage 5W.0 recorded the exact stable `v0.1.0` tag target
and commands without creating or pushing the tag. Stage 5W.0.1 created and
pushed that exact annotated stable tag. Stage 5W.0.2 verified isolated package
artifacts built from exact `v0.1.0`. Stage 5W.0.3 verified isolated
installation plus help-only CLI smoke from exact `v0.1.0`. Stage 5W.1
prepared main PyPI Trusted Publishing without publishing. Stage 5W.2 recorded
the user-attested exact publisher tuple and verified the local trust controls
without publishing. Stage 5W.3 published exact stable tag `v0.1.0` once through
Trusted Publishing and publicly verified main PyPI version `0.1.0`. Stage
5W.4 verified fresh main PyPI installation, installed metadata, and help-only
CLI entrypoints. Stage 5X recommends a separate GitHub Release creation stage
for `v0.1.0`; no GitHub Release was created during the decision. Stage 5X.1
created and verified the GitHub Release for existing stable tag `v0.1.0` and
closed release-chain `0.1.0`. Stage 5Y.0 added mirrored Russian and English
installation and first-run documentation for PyPI, repository, developer, and
upgrade paths. Stage 5Z.0 published and verified patch release `0.1.1`, created
its GitHub Release, and closed release-chain `0.1.1`.

Stage 5P.1 Ruff formatting remediation is recorded in [`reports/STAGE_5P_1_RUFF_FORMATTING_REMEDIATION_REPORT.md`](reports/STAGE_5P_1_RUFF_FORMATTING_REMEDIATION_REPORT.md).
Stage 5P.2 target identity history duplicate observation remediation is recorded in [`reports/STAGE_5P_2_TARGET_IDENTITY_HISTORY_DUPLICATE_OBSERVATION_REMEDIATION_REPORT.md`](reports/STAGE_5P_2_TARGET_IDENTITY_HISTORY_DUPLICATE_OBSERVATION_REMEDIATION_REPORT.md).
Stage 5P post-refactor full verification is recorded as passed and Stage 5Q is unblocked in [`reports/STAGE_5P_POST_REFACTOR_FULL_VERIFICATION_REPORT.md`](reports/STAGE_5P_POST_REFACTOR_FULL_VERIFICATION_REPORT.md).
Stage 5Q.0 public docs / CLI alignment is recorded as passed and Stage 5Q.1 is unblocked in [`reports/STAGE_5Q_0_PUBLIC_DOCS_CLI_ALIGNMENT_REPORT.md`](reports/STAGE_5Q_0_PUBLIC_DOCS_CLI_ALIGNMENT_REPORT.md).
Stage 5Q.1 packaging metadata / dependency readiness is recorded as passed and Stage 5Q.2 is unblocked in [`reports/STAGE_5Q_1_PACKAGING_METADATA_DEPENDENCY_READINESS_REPORT.md`](reports/STAGE_5Q_1_PACKAGING_METADATA_DEPENDENCY_READINESS_REPORT.md).
Stage 5Q.2 privacy / deferred areas audit is recorded as passed and Stage 5Q.3 is unblocked in [`reports/STAGE_5Q_2_PRIVACY_DEFERRED_AREAS_AUDIT_REPORT.md`](reports/STAGE_5Q_2_PRIVACY_DEFERRED_AREAS_AUDIT_REPORT.md).
Stage 5Q.3 release candidate checklist decision is recorded as passed and only Stage 5R.0 is authorized next in [`reports/STAGE_5Q_RELEASE_CANDIDATE_CHECKLIST_REPORT.md`](reports/STAGE_5Q_RELEASE_CANDIDATE_CHECKLIST_REPORT.md); its conservative notes draft is [`reports/STAGE_5Q_RELEASE_CANDIDATE_NOTES_DRAFT.md`](reports/STAGE_5Q_RELEASE_CANDIDATE_NOTES_DRAFT.md).
Stage 5R.0 package build dry-run is recorded as passed and Stage 5R.1 is unblocked in [`reports/STAGE_5R_0_PACKAGE_BUILD_DRY_RUN_REPORT.md`](reports/STAGE_5R_0_PACKAGE_BUILD_DRY_RUN_REPORT.md).
Stage 5R.1 isolated wheel install / CLI smoke is recorded as passed and Stage 5S is unblocked in [`reports/STAGE_5R_BUILD_AND_INSTALL_DRY_RUN_REPORT.md`](reports/STAGE_5R_BUILD_AND_INSTALL_DRY_RUN_REPORT.md).
Stage 5S release candidate tag plan is recorded as passed in [`reports/STAGE_5S_RELEASE_CANDIDATE_TAG_PLAN_REPORT.md`](reports/STAGE_5S_RELEASE_CANDIDATE_TAG_PLAN_REPORT.md); tag execution remains a separate explicitly authorized stage.
Stage 5T stable release decision keeps the project at release-candidate status because RC tag execution and post-RC smoke evidence are absent; see [`reports/STAGE_5T_STABLE_RELEASE_DECISION_REPORT.md`](reports/STAGE_5T_STABLE_RELEASE_DECISION_REPORT.md).
Stage 5U created and pushed annotated RC tag `v0.1.0-rc1`; post-RC smoke remains a separate stage; see [`reports/STAGE_5U_CREATE_RELEASE_CANDIDATE_TAG_REPORT.md`](reports/STAGE_5U_CREATE_RELEASE_CANDIDATE_TAG_REPORT.md).
Stage 5U.1 verified that exact RC tag `v0.1.0-rc1` builds, installs, and passes help-only CLI smoke; see [`reports/STAGE_5U_1_POST_RC_TAG_SMOKE_FROM_TAG_REPORT.md`](reports/STAGE_5U_1_POST_RC_TAG_SMOKE_FROM_TAG_REPORT.md).
Stage 5U.2 selected the compatible MIT license metadata form for Stage 5U.3; see [`reports/STAGE_5U_2_LICENSE_METADATA_DECISION_REPORT.md`](reports/STAGE_5U_2_LICENSE_METADATA_DECISION_REPORT.md).
Stage 5U.3 applied MIT license metadata and public/package documentation notes; see [`reports/STAGE_5U_3_LICENSE_METADATA_APPLICATION_REPORT.md`](reports/STAGE_5U_3_LICENSE_METADATA_APPLICATION_REPORT.md).
Stage 5U.4 verified built package artifacts and MIT metadata; see [`reports/STAGE_5U_4_LICENSE_METADATA_PACKAGE_VERIFICATION_REPORT.md`](reports/STAGE_5U_4_LICENSE_METADATA_PACKAGE_VERIFICATION_REPORT.md).
Stage 5V determined that `v0.1.0-rc1` predates final MIT metadata and requires a new RC tag before TestPyPI; see [`reports/STAGE_5V_TESTPYPI_PUBLISH_PREPARATION_REPORT.md`](reports/STAGE_5V_TESTPYPI_PUBLISH_PREPARATION_REPORT.md).
Stage 5U.5 recorded the exact eligible commit and annotated `v0.1.0-rc2` tag contract; see [`reports/STAGE_5U_5_RC2_TAG_PLAN_REPORT.md`](reports/STAGE_5U_5_RC2_TAG_PLAN_REPORT.md).
Stage 5U.6 created and pushed annotated tag `v0.1.0-rc2` on the approved commit; see [`reports/STAGE_5U_6_CREATE_RC2_TAG_REPORT.md`](reports/STAGE_5U_6_CREATE_RC2_TAG_REPORT.md).
Stage 5U.7 verified exact `v0.1.0-rc2` package artifacts, metadata, and checksums without install or publish; see [`reports/STAGE_5U_7_RC2_PACKAGE_ARTIFACT_VERIFICATION_REPORT.md`](reports/STAGE_5U_7_RC2_PACKAGE_ARTIFACT_VERIFICATION_REPORT.md).
Stage 5U.8 verified exact `v0.1.0-rc2` isolated wheel installation and scoped help entrypoints; see [`reports/STAGE_5U_8_RC2_ISOLATED_INSTALL_SMOKE_REPORT.md`](reports/STAGE_5U_8_RC2_ISOLATED_INSTALL_SMOKE_REPORT.md).
Stage 5V.1 classified the public TestPyPI/PyPI name and version state and recorded the manual TestPyPI token contract; see [`reports/STAGE_5V_1_TESTPYPI_NAME_AUTH_PREPARATION_REPORT.md`](reports/STAGE_5V_1_TESTPYPI_NAME_AUTH_PREPARATION_REPORT.md).
Stage 5V.2 prepared a manual, exact-tag, OIDC-only GitHub Actions workflow for TestPyPI without publishing; see [`reports/STAGE_5V_2_TESTPYPI_TRUSTED_PUBLISHING_SETUP_REPORT.md`](reports/STAGE_5V_2_TESTPYPI_TRUSTED_PUBLISHING_SETUP_REPORT.md).
Stage 5V.3 registered the exact TestPyPI pending publisher and GitHub Environment without dispatching or publishing; see [`reports/STAGE_5V_3_TESTPYPI_TRUSTED_PUBLISHER_REGISTRATION_REPORT.md`](reports/STAGE_5V_3_TESTPYPI_TRUSTED_PUBLISHER_REGISTRATION_REPORT.md).
Stage 5V.4 published exact `v0.1.0-rc2` artifacts once through Trusted Publishing and publicly verified TestPyPI version `0.1.0`; see [`reports/STAGE_5V_4_TESTPYPI_WORKFLOW_PUBLISH_REPORT.md`](reports/STAGE_5V_4_TESTPYPI_WORKFLOW_PUBLISH_REPORT.md).
Stage 5V.5 verified public TestPyPI installation of `tg-msg-manager==0.1.0`, expected metadata, and help-only CLI entrypoints; see [`reports/STAGE_5V_5_TESTPYPI_INSTALL_SMOKE_REPORT.md`](reports/STAGE_5V_5_TESTPYPI_INSTALL_SMOKE_REPORT.md).
Stage 5W verified main PyPI preparation and requires stable tag `v0.1.0` before main PyPI Trusted Publishing; see [`reports/STAGE_5W_PYPI_PUBLISH_PREPARATION_REPORT.md`](reports/STAGE_5W_PYPI_PUBLISH_PREPARATION_REPORT.md).
Stage 5W.0 planned stable tag `v0.1.0` on the verified RC2 peeled target and authorized only a separate tag-creation stage next; see [`reports/STAGE_5W_0_STABLE_TAG_V0_1_0_PLAN_REPORT.md`](reports/STAGE_5W_0_STABLE_TAG_V0_1_0_PLAN_REPORT.md).
Stage 5W.0.1 created and pushed annotated stable tag `v0.1.0` on the verified RC2 peeled target; package artifact verification remains separate; see [`reports/STAGE_5W_0_1_CREATE_STABLE_TAG_V0_1_0_REPORT.md`](reports/STAGE_5W_0_1_CREATE_STABLE_TAG_V0_1_0_REPORT.md).
Stage 5W.0.2 verified exact stable-tag wheel/sdist artifacts, metadata, license, entry point, and checksums without install or publish; see [`reports/STAGE_5W_0_2_STABLE_TAG_PACKAGE_ARTIFACT_VERIFICATION_REPORT.md`](reports/STAGE_5W_0_2_STABLE_TAG_PACKAGE_ARTIFACT_VERIFICATION_REPORT.md).
Stage 5W.0.3 verified isolated installation of the exact stable-tag wheel, installed metadata, and help-only CLI entrypoints; see [`reports/STAGE_5W_0_3_STABLE_TAG_ISOLATED_INSTALL_SMOKE_REPORT.md`](reports/STAGE_5W_0_3_STABLE_TAG_ISOLATED_INSTALL_SMOKE_REPORT.md).
Stage 5W.1 prepared a manual exact-tag OIDC workflow and GitHub Environment `pypi` without publishing; see [`reports/STAGE_5W_1_PYPI_TRUSTED_PUBLISHING_SETUP_REPORT.md`](reports/STAGE_5W_1_PYPI_TRUSTED_PUBLISHING_SETUP_REPORT.md).
Stage 5W.2 recorded the user-confirmed exact main PyPI Trusted Publisher tuple and verified repository trust controls without dispatching or publishing; see [`reports/STAGE_5W_2_PYPI_TRUSTED_PUBLISHER_REGISTRATION_REPORT.md`](reports/STAGE_5W_2_PYPI_TRUSTED_PUBLISHER_REGISTRATION_REPORT.md).
Stage 5W.3 published exact stable tag `v0.1.0` once through Trusted Publishing and publicly verified main PyPI version `0.1.0`; see [`reports/STAGE_5W_3_PYPI_WORKFLOW_PUBLISH_REPORT.md`](reports/STAGE_5W_3_PYPI_WORKFLOW_PUBLISH_REPORT.md).
Stage 5W.4 verified fresh main PyPI installation of `tg-msg-manager==0.1.0`, installed metadata, and help-only CLI entrypoints; see [`reports/STAGE_5W_4_PYPI_INSTALL_SMOKE_REPORT.md`](reports/STAGE_5W_4_PYPI_INSTALL_SMOKE_REPORT.md).
Stage 5X selected a separate GitHub Release creation stage for `v0.1.0` without creating the release; see [`reports/STAGE_5X_GITHUB_RELEASE_OR_RELEASE_CHAIN_CLOSEOUT_DECISION_REPORT.md`](reports/STAGE_5X_GITHUB_RELEASE_OR_RELEASE_CHAIN_CLOSEOUT_DECISION_REPORT.md).
Stage 5X.1 created and verified the GitHub Release for existing stable tag `v0.1.0` and closed release-chain `0.1.0`; see [`reports/STAGE_5X_1_GITHUB_RELEASE_CREATION_REPORT.md`](reports/STAGE_5X_1_GITHUB_RELEASE_CREATION_REPORT.md).
Stage 5Y.0 added bilingual installation and first-run documentation; see [`reports/STAGE_5Y_0_BILINGUAL_INSTALLATION_DOCUMENTATION_REPORT.md`](reports/STAGE_5Y_0_BILINGUAL_INSTALLATION_DOCUMENTATION_REPORT.md).
Stage 5Z.0 published and verified patch release `0.1.1`; see [`reports/STAGE_5Z_0_PATCH_RELEASE_V0_1_1_REPORT.md`](reports/STAGE_5Z_0_PATCH_RELEASE_V0_1_1_REPORT.md).
Stage 5Z.1 fixed first-run config bootstrap and published patch release `0.1.2`; see [`reports/STAGE_5Z_1_FIRST_RUN_CONFIG_BOOTSTRAP_AND_PATCH_RELEASE_V0_1_2_REPORT.md`](reports/STAGE_5Z_1_FIRST_RUN_CONFIG_BOOTSTRAP_AND_PATCH_RELEASE_V0_1_2_REPORT.md).
Stage 5O.14 test suite component split is recorded in [`reports/STAGE_5O_14_TEST_SUITE_COMPONENT_SPLIT_REPORT.md`](reports/STAGE_5O_14_TEST_SUITE_COMPONENT_SPLIT_REPORT.md).
Stage 5O.13 storage compatibility guardrails is recorded in [`reports/STAGE_5O_13_STORAGE_COMPATIBILITY_GUARDRAILS_REPORT.md`](reports/STAGE_5O_13_STORAGE_COMPATIBILITY_GUARDRAILS_REPORT.md).
Stage 5O.12 context sync dependency extraction is recorded in [`reports/STAGE_5O_12_CONTEXT_SYNC_DEPENDENCY_EXTRACTION_REPORT.md`](reports/STAGE_5O_12_CONTEXT_SYNC_DEPENDENCY_EXTRACTION_REPORT.md).
Stage 5O.11 context sync dependency precheck is recorded in [`reports/STAGE_5O_11_CONTEXT_SYNC_DEPENDENCY_PRECHECK_REPORT.md`](reports/STAGE_5O_11_CONTEXT_SYNC_DEPENDENCY_PRECHECK_REPORT.md).
Stage 5O.10 cleaner artifact purger is recorded in [`reports/STAGE_5O_10_CLEANER_ARTIFACT_PURGER_REPORT.md`](reports/STAGE_5O_10_CLEANER_ARTIFACT_PURGER_REPORT.md).
Stage 5O.9 file writer state boundary is recorded in [`reports/STAGE_5O_9_FILE_WRITER_STATE_BOUNDARY_REPORT.md`](reports/STAGE_5O_9_FILE_WRITER_STATE_BOUNDARY_REPORT.md).
Stage 5O.8 discussion builder split is recorded in [`reports/STAGE_5O_8_DISCUSSION_BUILDER_SPLIT_REPORT.md`](reports/STAGE_5O_8_DISCUSSION_BUILDER_SPLIT_REPORT.md).
Stage 5O.7 CLI option boundary is recorded in [`reports/STAGE_5O_7_CLI_OPTION_BOUNDARY_REPORT.md`](reports/STAGE_5O_7_CLI_OPTION_BOUNDARY_REPORT.md).
Stage 5O.6 DB export run coordinator extraction is recorded in [`reports/STAGE_5O_6_DB_EXPORT_RUN_COORDINATOR_EXTRACTION_REPORT.md`](reports/STAGE_5O_6_DB_EXPORT_RUN_COORDINATOR_EXTRACTION_REPORT.md).
Stage 5O.5 DB export run lifecycle characterization is recorded in [`reports/STAGE_5O_5_DB_EXPORT_RUN_LIFECYCLE_CHARACTERIZATION_REPORT.md`](reports/STAGE_5O_5_DB_EXPORT_RUN_LIFECYCLE_CHARACTERIZATION_REPORT.md).
Stage 5O.4 dataset contract constants is recorded in [`reports/STAGE_5O_4_DATASET_CONTRACT_CONSTANTS_REPORT.md`](reports/STAGE_5O_4_DATASET_CONTRACT_CONSTANTS_REPORT.md).
Stage 5O.3 CLI parser media size error is recorded in [`reports/STAGE_5O_3_CLI_PARSER_MEDIA_SIZE_ERROR_REPORT.md`](reports/STAGE_5O_3_CLI_PARSER_MEDIA_SIZE_ERROR_REPORT.md).
Stage 5O.2 i18n parity guard is recorded in [`reports/STAGE_5O_2_I18N_PARITY_GUARD_REPORT.md`](reports/STAGE_5O_2_I18N_PARITY_GUARD_REPORT.md).
Stage 5O.1 config loading source cleanup is recorded in [`reports/STAGE_5O_1_CONFIG_LOADING_SOURCE_CLEANUP_REPORT.md`](reports/STAGE_5O_1_CONFIG_LOADING_SOURCE_CLEANUP_REPORT.md).
Stage 5O.0 refactoring guardrails is recorded in [`reports/STAGE_5O_0_REFACTORING_GUARDRAILS_REPORT.md`](reports/STAGE_5O_0_REFACTORING_GUARDRAILS_REPORT.md).
Stage 5N.1 target names history CLI is recorded in [`reports/STAGE_5N_1_TARGET_NAMES_HISTORY_CLI_REPORT.md`](reports/STAGE_5N_1_TARGET_NAMES_HISTORY_CLI_REPORT.md).
Stage 5N.0 target names history read model is recorded in [`reports/STAGE_5N_0_TARGET_NAMES_HISTORY_READ_MODEL_REPORT.md`](reports/STAGE_5N_0_TARGET_NAMES_HISTORY_READ_MODEL_REPORT.md).
Stage 5M.6 operational risk notes is recorded in [`reports/STAGE_5M_6_OPERATIONAL_RISK_NOTES_REPORT.md`](reports/STAGE_5M_6_OPERATIONAL_RISK_NOTES_REPORT.md).
Stage 5M.5 deferred contract coverage prioritization is recorded in [`reports/STAGE_5M_5_DEFERRED_CONTRACT_COVERAGE_PRIORITIZATION_REPORT.md`](reports/STAGE_5M_5_DEFERRED_CONTRACT_COVERAGE_PRIORITIZATION_REPORT.md).
Stage 5M.3 schedule / limit / entrypoint UX audit is recorded in [`reports/STAGE_5M_3_SCHEDULE_LIMIT_ENTRYPOINT_UX_AUDIT_REPORT.md`](reports/STAGE_5M_3_SCHEDULE_LIMIT_ENTRYPOINT_UX_AUDIT_REPORT.md).
Stage 5M.2 public docs feature status alignment is recorded in [`reports/STAGE_5M_2_PUBLIC_DOCS_FEATURE_STATUS_ALIGNMENT_REPORT.md`](reports/STAGE_5M_2_PUBLIC_DOCS_FEATURE_STATUS_ALIGNMENT_REPORT.md).
Stage 5M.0 external risk audit verification is recorded in [`reports/STAGE_5M_0_EXTERNAL_RISK_AUDIT_VERIFICATION_REPORT.md`](reports/STAGE_5M_0_EXTERNAL_RISK_AUDIT_VERIFICATION_REPORT.md).
Stage 5L.1 release candidate decision recheck is recorded in [`reports/STAGE_5L_1_RELEASE_CANDIDATE_DECISION_RECHECK_REPORT.md`](reports/STAGE_5L_1_RELEASE_CANDIDATE_DECISION_RECHECK_REPORT.md).
Stage 5K.4 release candidate decision report is recorded in [`reports/STAGE_5K_4_RELEASE_CANDIDATE_DECISION_REPORT.md`](reports/STAGE_5K_4_RELEASE_CANDIDATE_DECISION_REPORT.md).
Stage 5K.3 local verification matrix is recorded in [`reports/STAGE_5K_3_LOCAL_VERIFICATION_MATRIX_REPORT.md`](reports/STAGE_5K_3_LOCAL_VERIFICATION_MATRIX_REPORT.md).
Stage 5K.2 documentation / privacy / changelog release audit is recorded in [`reports/STAGE_5K_2_DOCUMENTATION_PRIVACY_CHANGELOG_RELEASE_AUDIT_REPORT.md`](reports/STAGE_5K_2_DOCUMENTATION_PRIVACY_CHANGELOG_RELEASE_AUDIT_REPORT.md).
Stage 5K.1 packaging metadata readiness audit is recorded in [`reports/STAGE_5K_1_PACKAGING_METADATA_READINESS_AUDIT_REPORT.md`](reports/STAGE_5K_1_PACKAGING_METADATA_READINESS_AUDIT_REPORT.md).
Stage 5K.0 release checklist scope / no-publish boundary is recorded in [`reports/STAGE_5K_0_RELEASE_CHECKLIST_SCOPE_NO_PUBLISH_BOUNDARY_REPORT.md`](reports/STAGE_5K_0_RELEASE_CHECKLIST_SCOPE_NO_PUBLISH_BOUNDARY_REPORT.md).
Stage 4C.0 Unit A is recorded in [`reports/STAGE_4C_0_STRUCTURAL_DECOMPOSITION_REPORT.md`](reports/STAGE_4C_0_STRUCTURAL_DECOMPOSITION_REPORT.md).
Stage 4C.0B is recorded in [`reports/STAGE_4C_0B_CHANNEL_EXPORT_WORKFLOW_SPLIT_REPORT.md`](reports/STAGE_4C_0B_CHANNEL_EXPORT_WORKFLOW_SPLIT_REPORT.md).
Stage 4C.0C is recorded in [`reports/STAGE_4C_0C_TEST_LAYOUT_GROUPING_REPORT.md`](reports/STAGE_4C_0C_TEST_LAYOUT_GROUPING_REPORT.md).
Stage 4C.0 architecture stabilization audit is recorded in [`reports/STAGE_4C_0_ARCHITECTURE_STABILIZATION_AUDIT_BEFORE_EXPANSION_REPORT.md`](reports/STAGE_4C_0_ARCHITECTURE_STABILIZATION_AUDIT_BEFORE_EXPANSION_REPORT.md).
Stage 4C.1 architecture rules sync is recorded in [`reports/STAGE_4C_1_ARCHITECTURE_RULES_SYNC_AFTER_AUDIT_REPORT.md`](reports/STAGE_4C_1_ARCHITECTURE_RULES_SYNC_AFTER_AUDIT_REPORT.md).
Stage 4D.0 dataset contract v1 design is recorded in [`reports/STAGE_4D_0_DATASET_CONTRACT_V1_DESIGN_REPORT.md`](reports/STAGE_4D_0_DATASET_CONTRACT_V1_DESIGN_REPORT.md).
Stage 4D.1 dataset validation contract alignment is recorded in [`reports/STAGE_4D_1_DATASET_VALIDATION_CONTRACT_ALIGNMENT_REPORT.md`](reports/STAGE_4D_1_DATASET_VALIDATION_CONTRACT_ALIGNMENT_REPORT.md).
Stage 4D.2 read-only dataset doctor is recorded in [`reports/STAGE_4D_2_READ_ONLY_DATASET_DOCTOR_REPORT.md`](reports/STAGE_4D_2_READ_ONLY_DATASET_DOCTOR_REPORT.md).
Stage 5A.0 external post-processing boundary skeleton is recorded in [`reports/STAGE_5A_0_EXTERNAL_POST_PROCESSING_BOUNDARY_SKELETON_REPORT.md`](reports/STAGE_5A_0_EXTERNAL_POST_PROCESSING_BOUNDARY_SKELETON_REPORT.md).
Stage 5B.0 scalability baseline before growth hardening is recorded in [`reports/STAGE_5B_0_SCALABILITY_BASELINE_REPORT.md`](reports/STAGE_5B_0_SCALABILITY_BASELINE_REPORT.md).
Stage 5B.1 private archive batched storage flush is recorded in [`reports/STAGE_5B_1_PRIVATE_ARCHIVE_BATCHED_STORAGE_FLUSH_REPORT.md`](reports/STAGE_5B_1_PRIVATE_ARCHIVE_BATCHED_STORAGE_FLUSH_REPORT.md).
Stage 5B.2 channel export post buffer boundaries is recorded in [`reports/STAGE_5B_2_CHANNEL_EXPORT_POST_BUFFER_BOUNDARIES_REPORT.md`](reports/STAGE_5B_2_CHANNEL_EXPORT_POST_BUFFER_BOUNDARIES_REPORT.md).
Stage 5B.3 DB export memory boundaries is recorded in [`reports/STAGE_5B_3_DB_EXPORT_MEMORY_BOUNDARIES_REPORT.md`](reports/STAGE_5B_3_DB_EXPORT_MEMORY_BOUNDARIES_REPORT.md).
Stage 5B.4 SQLite write queue backpressure is recorded in [`reports/STAGE_5B_4_SQLITE_WRITE_QUEUE_BACKPRESSURE_REPORT.md`](reports/STAGE_5B_4_SQLITE_WRITE_QUEUE_BACKPRESSURE_REPORT.md).
Stage 5B.5 SQLite schema decomposition plan is recorded in [`reports/STAGE_5B_5_SQLITE_SCHEMA_DECOMPOSITION_PLAN_REPORT.md`](reports/STAGE_5B_5_SQLITE_SCHEMA_DECOMPOSITION_PLAN_REPORT.md).
Stage 5C.0 dataset contract coverage matrix is recorded in [`reports/STAGE_5C_0_DATASET_CONTRACT_COVERAGE_MATRIX_REPORT.md`](reports/STAGE_5C_0_DATASET_CONTRACT_COVERAGE_MATRIX_REPORT.md).
Stage 5C.1 pytest collection hygiene is recorded in [`reports/STAGE_5C_1_PYTEST_COLLECTION_HYGIENE_REPORT.md`](reports/STAGE_5C_1_PYTEST_COLLECTION_HYGIENE_REPORT.md).
Stage 5C.2 skill routing fallback verification is recorded in [`reports/STAGE_5C_2_SKILL_ROUTING_FALLBACK_VERIFICATION_REPORT.md`](reports/STAGE_5C_2_SKILL_ROUTING_FALLBACK_VERIFICATION_REPORT.md).
Stage 5C.3 CLI / README / COMMANDS parity audit is recorded in [`reports/STAGE_5C_3_CLI_README_COMMANDS_PARITY_AUDIT_REPORT.md`](reports/STAGE_5C_3_CLI_README_COMMANDS_PARITY_AUDIT_REPORT.md).
Stage 5C.4 privacy and sensitive artifacts guide is recorded in [`reports/STAGE_5C_4_PRIVACY_SENSITIVE_ARTIFACTS_GUIDE_REPORT.md`](reports/STAGE_5C_4_PRIVACY_SENSITIVE_ARTIFACTS_GUIDE_REPORT.md).
Stage 5C.5 package identity / version policy cleanup is recorded in [`reports/STAGE_5C_5_PACKAGE_IDENTITY_VERSION_POLICY_CLEANUP_REPORT.md`](reports/STAGE_5C_5_PACKAGE_IDENTITY_VERSION_POLICY_CLEANUP_REPORT.md).
Stage 5D.0 SQLite schema split stage 1 is recorded in [`reports/STAGE_5D_0_SQLITE_SCHEMA_SPLIT_STAGE_1_REPORT.md`](reports/STAGE_5D_0_SQLITE_SCHEMA_SPLIT_STAGE_1_REPORT.md).
Stage 5D.1 dataset contract gap closure plan is recorded in [`reports/STAGE_5D_1_DATASET_CONTRACT_GAP_CLOSURE_PLAN_REPORT.md`](reports/STAGE_5D_1_DATASET_CONTRACT_GAP_CLOSURE_PLAN_REPORT.md).
Stage 5D.2 run changelog key set contract tests is recorded in [`reports/STAGE_5D_2_RUN_CHANGELOG_KEY_SET_CONTRACT_TESTS_REPORT.md`](reports/STAGE_5D_2_RUN_CHANGELOG_KEY_SET_CONTRACT_TESTS_REPORT.md).
Stage 5D.3 TXT projection contract clarification is recorded in [`reports/STAGE_5D_3_TXT_PROJECTION_CONTRACT_CLARIFICATION_REPORT.md`](reports/STAGE_5D_3_TXT_PROJECTION_CONTRACT_CLARIFICATION_REPORT.md).
Stage 5D.4 channel export mode matrix tests are recorded in [`reports/STAGE_5D_4_CHANNEL_EXPORT_MODE_MATRIX_TESTS_REPORT.md`](reports/STAGE_5D_4_CHANNEL_EXPORT_MODE_MATRIX_TESTS_REPORT.md).
Stage 5D.5 user quickstart safe first export guide is recorded in [`reports/STAGE_5D_5_USER_QUICKSTART_SAFE_FIRST_EXPORT_GUIDE_REPORT.md`](reports/STAGE_5D_5_USER_QUICKSTART_SAFE_FIRST_EXPORT_GUIDE_REPORT.md).
Stage 5E.0 SQLite schema split stage 2 migration helpers precheck is recorded in [`reports/STAGE_5E_0_SQLITE_SCHEMA_SPLIT_STAGE_2_MIGRATION_HELPERS_PRECHECK_REPORT.md`](reports/STAGE_5E_0_SQLITE_SCHEMA_SPLIT_STAGE_2_MIGRATION_HELPERS_PRECHECK_REPORT.md).
Stage 5E.1 SQLite schema split stage 2 migration helper extraction is recorded in [`reports/STAGE_5E_1_SQLITE_SCHEMA_SPLIT_STAGE_2_MIGRATION_HELPER_EXTRACTION_REPORT.md`](reports/STAGE_5E_1_SQLITE_SCHEMA_SPLIT_STAGE_2_MIGRATION_HELPER_EXTRACTION_REPORT.md).
Stage 5E.2 SQLite schema split regression expansion is recorded in [`reports/STAGE_5E_2_SQLITE_SCHEMA_SPLIT_REGRESSION_EXPANSION_REPORT.md`](reports/STAGE_5E_2_SQLITE_SCHEMA_SPLIT_REGRESSION_EXPANSION_REPORT.md).
Stage 5F.0 current architecture / context refresh is recorded in [`reports/STAGE_5F_0_CURRENT_ARCHITECTURE_CONTEXT_REFRESH_REPORT.md`](reports/STAGE_5F_0_CURRENT_ARCHITECTURE_CONTEXT_REFRESH_REPORT.md).
Stage 5F.1 user documentation navigation audit / quickstart consolidation is recorded in [`reports/STAGE_5F_1_USER_DOCUMENTATION_NAVIGATION_AUDIT_QUICKSTART_CONSOLIDATION_REPORT.md`](reports/STAGE_5F_1_USER_DOCUMENTATION_NAVIGATION_AUDIT_QUICKSTART_CONSOLIDATION_REPORT.md).
Stage 5F.2 synthetic channel dataset example is recorded in [`reports/STAGE_5F_2_SYNTHETIC_CHANNEL_DATASET_EXAMPLE_REPORT.md`](reports/STAGE_5F_2_SYNTHETIC_CHANNEL_DATASET_EXAMPLE_REPORT.md).
Stage 5F.3 dataset doctor output examples is recorded in [`reports/STAGE_5F_3_DATASET_DOCTOR_OUTPUT_EXAMPLES_REPORT.md`](reports/STAGE_5F_3_DATASET_DOCTOR_OUTPUT_EXAMPLES_REPORT.md).
Stage 5F.4 post-processing example catalogue refinement is recorded in [`reports/STAGE_5F_4_POST_PROCESSING_EXAMPLE_CATALOGUE_REFINEMENT_REPORT.md`](reports/STAGE_5F_4_POST_PROCESSING_EXAMPLE_CATALOGUE_REFINEMENT_REPORT.md).
Stage 5F.5 static dataset summary report design is recorded in [`reports/STAGE_5F_5_STATIC_DATASET_SUMMARY_REPORT_DESIGN_REPORT.md`](reports/STAGE_5F_5_STATIC_DATASET_SUMMARY_REPORT_DESIGN_REPORT.md).
Stage 5G.0 post-5F documentation / examples consistency audit is recorded in [`reports/STAGE_5G_0_POST_5F_DOCUMENTATION_EXAMPLES_CONSISTENCY_AUDIT_REPORT.md`](reports/STAGE_5G_0_POST_5F_DOCUMENTATION_EXAMPLES_CONSISTENCY_AUDIT_REPORT.md).
Stage 5G.1 synthetic examples regression check is recorded in [`reports/STAGE_5G_1_SYNTHETIC_EXAMPLES_REGRESSION_CHECK_REPORT.md`](reports/STAGE_5G_1_SYNTHETIC_EXAMPLES_REGRESSION_CHECK_REPORT.md).
Stage 5G.2 non-channel dataset contract precheck is recorded in [`reports/STAGE_5G_2_NON_CHANNEL_DATASET_CONTRACT_PRECHECK_REPORT.md`](reports/STAGE_5G_2_NON_CHANNEL_DATASET_CONTRACT_PRECHECK_REPORT.md).
Stage 5G.3 user-facing release readiness audit is recorded in [`reports/STAGE_5G_3_USER_FACING_RELEASE_READINESS_AUDIT_REPORT.md`](reports/STAGE_5G_3_USER_FACING_RELEASE_READINESS_AUDIT_REPORT.md).
Stage 5H.0 changelog / release notes refresh precheck is recorded in [`reports/STAGE_5H_0_CHANGELOG_RELEASE_NOTES_REFRESH_PRECHECK_REPORT.md`](reports/STAGE_5H_0_CHANGELOG_RELEASE_NOTES_REFRESH_PRECHECK_REPORT.md).
Stage 5H.1 non-channel export contract design precheck is recorded in [`reports/STAGE_5H_1_NON_CHANNEL_EXPORT_CONTRACT_DESIGN_PRECHECK_REPORT.md`](reports/STAGE_5H_1_NON_CHANNEL_EXPORT_CONTRACT_DESIGN_PRECHECK_REPORT.md).
Stage 5H.2 user + DB export synthetic fixtures plan is recorded in [`reports/STAGE_5H_2_USER_DB_EXPORT_SYNTHETIC_FIXTURES_PLAN_REPORT.md`](reports/STAGE_5H_2_USER_DB_EXPORT_SYNTHETIC_FIXTURES_PLAN_REPORT.md).
Stage 5H.3 private archive contract deferred decision is recorded in [`reports/STAGE_5H_3_PRIVATE_ARCHIVE_CONTRACT_DEFERRED_DECISION_REPORT.md`](reports/STAGE_5H_3_PRIVATE_ARCHIVE_CONTRACT_DEFERRED_DECISION_REPORT.md).
Stage 5I.0 non-channel synthetic fixtures stage files is recorded in [`reports/STAGE_5I_0_NON_CHANNEL_SYNTHETIC_FIXTURES_STAGE_FILES_REPORT.md`](reports/STAGE_5I_0_NON_CHANNEL_SYNTHETIC_FIXTURES_STAGE_FILES_REPORT.md).
Stage 5I.1 user/db export synthetic fixture implementation is recorded in [`reports/STAGE_5I_1_USER_DB_EXPORT_SYNTHETIC_FIXTURE_IMPLEMENTATION_REPORT.md`](reports/STAGE_5I_1_USER_DB_EXPORT_SYNTHETIC_FIXTURE_IMPLEMENTATION_REPORT.md).
Stage 5I.2 non-channel contract test plan is recorded in [`reports/STAGE_5I_2_NON_CHANNEL_CONTRACT_TEST_PLAN_REPORT.md`](reports/STAGE_5I_2_NON_CHANNEL_CONTRACT_TEST_PLAN_REPORT.md).
Stage 5I.3 non-channel export contract v1 draft is recorded in [`reports/STAGE_5I_3_NON_CHANNEL_EXPORT_CONTRACT_V1_DRAFT_REPORT.md`](reports/STAGE_5I_3_NON_CHANNEL_EXPORT_CONTRACT_V1_DRAFT_REPORT.md).
Stage 5J.0 post-5I consistency audit is recorded in [`reports/STAGE_5J_0_POST_5I_CONSISTENCY_AUDIT_REPORT.md`](reports/STAGE_5J_0_POST_5I_CONSISTENCY_AUDIT_REPORT.md).
Stage 5J.1 non-channel contract tests implementation is recorded in [`reports/STAGE_5J_1_NON_CHANNEL_CONTRACT_TESTS_IMPLEMENTATION_REPORT.md`](reports/STAGE_5J_1_NON_CHANNEL_CONTRACT_TESTS_IMPLEMENTATION_REPORT.md).
Stage 5J.2 fixture-to-contract verification is recorded in [`reports/STAGE_5J_2_FIXTURE_TO_CONTRACT_VERIFICATION_REPORT.md`](reports/STAGE_5J_2_FIXTURE_TO_CONTRACT_VERIFICATION_REPORT.md).
Stage 5J.3 release readiness recheck / changelog finalization is recorded in [`reports/STAGE_5J_3_RELEASE_READINESS_RECHECK_CHANGELOG_FINALIZATION_REPORT.md`](reports/STAGE_5J_3_RELEASE_READINESS_RECHECK_CHANGELOG_FINALIZATION_REPORT.md).

The [`active/`](active/) directory must contain only unfinished or next active work. Do not leave completed stage task files, general launch prompts, prompt packs, or historical records there.

## Completed stages

Completed stage files under [`completed/`](completed/) are historical instructions. They show what an agent was asked to do at the time, but they are not current guidance.

Current completed prompt groups:

- Stage 7C.2 legacy null discussion batch compatibility bugfix prompt.
- Stage 7C.1 channel update interactive-menu parity task prompt.
- Stage 7C.0 bulk incremental channel update task prompt.
- Stage 7B.1 VPS state sync safety correction task prompt.
- Stage 7B.2 VPS systemd scheduler task prompt.
- Stage 7B.0 VPS Docker Compose deployment wrapper task prompt.
- Stage 7A.3 coverage and typecheck gate precheck task prompt.
- Stage 7A.2 fixture contract snapshot gate task prompt.
- Stage 7A.1 pytest authority and CI gate alignment task prompt.
- Stage 7A.0 test infrastructure baseline and hardening plan task prompt.
- Stage 6H.0 package changelog version history cleanup task prompt.
- Stage 6G.2 SQLite write path aggregator shrink task prompt.
- Stage 6G.1 internal import convergence task prompt.
- Stage 6G.0 compatibility surface baseline task prompt.
- Stage 6F.2 SQLite migration registry decision task prompt.
- Stage 6F.1 SQLite schema startup path split task prompt.
- Stage 6F.0 SQLite schema startup guardrails task prompt.
- Stage 6E.0 CI gate alignment and Ruff format guardrails task prompt.
- Stage 6D.1 throttler rate recovery task prompt.
- Stage 6D.0 FloodWait bounded retry task prompt.
- Stage 3A direct channel export task prompts.
- Stage 3B media hardening and stabilization task prompts.
- Stage 3C discussion export task prompts.
- Stage 3D.0 project governance and documentation reorganization task prompts.
- Stage 3D.1 stage lifecycle cleanup task prompt.
- Stage 3E.0 channel export service decomposition task prompt.
- Stage 3E.1 dataset atomic write / commit safety task prompt.
- Stage 3E.2 dataset schema contract tests task prompt.
- Stage 3E.3 state consistency hardening task prompt.
- Stage 3E.4 media filename / extension detection hardening task prompt.
- Stage 3E.5 interactive channel export options parity task prompt.
- Stage 4A dataset validation / inspection task prompts.
- Stage 4A.5 context-readable TXT export profile task prompts.
- Stage 4A.6 context-readable TXT fallback hardening task prompt.
- Stage 4A.7 DB export TXT profile parity task prompt.
- Stage 4A.8 discussion export policy hardening task prompt.
- Stage 4B.1 dataset integrity audit-only task prompt.
- Stage 4B.2 dataset validation hardening task prompt.
- Stage 4B.3 run changelog artifact task prompt.
- Stage 4C.0 architecture stabilization audit before expansion task prompt.
- Stage 4C.1 architecture rules sync after audit task prompt.
- Stage 4C.0B channel export workflow split task prompt.
- Stage 4C.0C test layout grouping task prompt.
- Stage 4D.0 dataset contract v1 design task prompt.
- Stage 4D.1 dataset validation contract alignment task prompt.
- Stage 4D.2 read-only dataset doctor task prompt.
- Stage 5A.0 external post-processing boundary skeleton task prompt.
- Stage 5B.0 scalability baseline before growth hardening task prompt.
- Stage 5B.1 private archive batched storage flush task prompt.
- Stage 5B.2 channel export post buffer boundaries task prompt.
- Stage 5B.3 DB export memory boundaries task prompt.
- Stage 5B.4 SQLite write queue backpressure task prompt.
- Stage 5B.5 SQLite schema decomposition plan task prompt.
- Stage 5C.0 dataset contract coverage matrix task prompt.
- Stage 5C.1 pytest collection hygiene task prompt.
- Stage 5C.2 skill routing fallback verification task prompt.
- Stage 5C.3 CLI / README / COMMANDS parity audit task prompt.
- Stage 5C.4 privacy and sensitive artifacts guide task prompt.
- Stage 5C.5 package identity / version policy cleanup task prompt.
- Stage 5D.0 SQLite schema split stage 1 task prompt.
- Stage 5D.1 dataset contract gap closure plan task prompt.
- Stage 5D.2 run changelog key set contract tests task prompt.
- Stage 5D.3 TXT projection contract clarification task prompt.
- Stage 5D.4 channel export mode matrix tests task prompt.
- Stage 5D.5 user quickstart safe first export guide task prompt.
- Stage 5E.0 SQLite schema split stage 2 migration helpers precheck task prompt.
- Stage 5E.1 SQLite schema split stage 2 migration helper extraction task prompt.
- Stage 5E.2 SQLite schema split regression expansion task prompt.
- Stage 5F.0 current architecture / context refresh task prompt.
- Stage 5F.1 user documentation navigation audit / quickstart consolidation task prompt.
- Stage 5F.2 synthetic channel dataset example task prompt.
- Stage 5F.3 dataset doctor output examples task prompt.
- Stage 5F.4 post-processing example catalogue refinement task prompt.
- Stage 5F.5 static dataset summary report design task prompt.
- Stage 5G.0 post-5F documentation / examples consistency audit task prompt.
- Stage 5G.1 synthetic examples regression check task prompt.
- Stage 5G.2 non-channel dataset contract precheck task prompt.
- Stage 5G.3 user-facing release readiness audit task prompt.
- Stage 5H.0 changelog / release notes refresh precheck task prompt.
- Stage 5H.1 non-channel export contract design precheck task prompt.
- Stage 5H.2 user + DB export synthetic fixtures plan task prompt.
- Stage 5H.3 private archive contract deferred decision task prompt.
- Stage 5I.0 non-channel synthetic fixtures stage files task prompt.
- Stage 5I.1 user/db export synthetic fixture implementation task prompt.
- Stage 5I.2 non-channel contract test plan task prompt.
- Stage 5I.3 non-channel export contract v1 draft task prompt.
- Stage 5J.0 post-5I consistency audit task prompt.
- Stage 5J.1 non-channel contract tests implementation task prompt.
- Stage 5J.2 fixture-to-contract verification task prompt.
- Stage 5J.3 release readiness recheck / changelog finalization task prompt.
- Stage 5K.0 release checklist scope / no-publish boundary task prompt.
- Stage 5K.1 packaging metadata readiness audit task prompt.
- Stage 5K.2 documentation / privacy / changelog release audit task prompt.
- Stage 5K.3 local verification matrix task prompt.
- Stage 5K.4 release candidate decision report task prompt.
- Stage 5L.1 release candidate decision recheck task prompt.
- Stage 5M.0 external risk audit verification task prompt.
- Stage 5M.2 public docs feature status alignment task prompt.
- Stage 5M.3 schedule / limit / entrypoint UX audit task prompt.
- Stage 5M.5 deferred contract coverage prioritization task prompt.
- Stage 5M.6 operational risk notes task prompt.
- Stage 5N.0 target names history read model task prompt.
- Stage 5N.1 target names history CLI task prompt.
- Stage 5O.0 refactoring guardrails task prompt.
- Stage 5O.1 config loading source cleanup task prompt.
- Stage 5O.2 i18n parity guard task prompt.
- Stage 5O.3 CLI parser media size error task prompt.
- Stage 5O.4 dataset contract constants task prompt.
- Stage 5O.5 DB export run lifecycle characterization task prompt.
- Stage 5O.6 DB export run coordinator extraction task prompt.
- Stage 5O.7 CLI option boundary task prompt.
- Stage 5O.8 discussion builder split task prompt.
- Stage 5O.11 context sync dependency precheck task prompt.
- Stage 5O.12 context sync dependency extraction task prompt.
- Stage 5O.13 storage compatibility guardrails task prompt.
- Stage 5O.14 test suite component split task prompt.
- Stage 5O.9 file writer state boundary task prompt.
- Stage 5P post-refactor full verification task prompt.
- Stage 5Y.0 bilingual installation documentation task prompt.
- Stage 5Z.0 patch release `v0.1.1` task prompt.
- Stage 5P.1 Ruff formatting remediation task prompt.
- Stage 5P.2 target identity history duplicate observation remediation task prompt.
- Stage 5Q.0 public docs / CLI alignment task prompt.
- Stage 5Q.1 packaging metadata / dependency readiness task prompt.
- Stage 5Q.2 privacy / deferred areas audit task prompt.
- Stage 5Q.3 release candidate checklist decision task prompt.
- Stage 5T stable release decision task prompt.
- Stage 5U create release candidate tag task prompt.
- Stage 5U.1 post-RC tag smoke from tag task prompt.
- Stage 5U.2 license metadata decision task prompt.
- Stage 5U.3 license metadata application task prompt.
- Stage 5U.4 license metadata package verification task prompt.
- Stage 5V TestPyPI publish source decision task prompt.
- Stage 5U.5 RC2 tag plan task prompt.
- Stage 5U.6 create RC2 tag task prompt.
- Stage 5U.7 RC2 package artifact verification task prompt.
- Stage 5U.8 RC2 isolated install smoke task prompt.
- Stage 5V.2 TestPyPI Trusted Publishing setup task prompt.
- Stage 5V.3 TestPyPI Trusted Publisher registration task prompt.
- Stage 5V.4 TestPyPI workflow publish task prompt.
- Stage 5V.5 TestPyPI install smoke task prompt.
- Stage 5W.0 stable tag v0.1.0 plan task prompt.
- Stage 5W.0.1 create stable tag v0.1.0 task prompt.
- Stage 5W.0.2 stable tag package artifact verification task prompt.
- Stage 5W.0.3 stable tag isolated install smoke task prompt.
- Stage 5W.2 PyPI Trusted Publisher registration task prompt.
- Stage 5W.3 PyPI workflow publish task prompt.
- Stage 5W.4 PyPI install smoke task prompt.
- Stage 5X GitHub Release or release-chain closeout decision task prompt.
- Stage 5X.1 GitHub Release creation task prompt.

Stage 5T stable release decision task files:

- [`completed/stage_5t_stable_release_decision.md`](completed/stage_5t_stable_release_decision.md)

Stage 5U create release candidate tag task files:

- [`completed/stage_5u_create_release_candidate_tag.md`](completed/stage_5u_create_release_candidate_tag.md)

Stage 5U.1 post-RC tag smoke from tag task files:

- [`completed/stage_5u_1_post_rc_tag_smoke_from_tag.md`](completed/stage_5u_1_post_rc_tag_smoke_from_tag.md)

Stage 5U.2 license metadata decision task files:

- [`completed/stage_5u_2_license_metadata_decision.md`](completed/stage_5u_2_license_metadata_decision.md)

Stage 5U.3 license metadata application task files:

- [`completed/stage_5u_3_license_metadata_application.md`](completed/stage_5u_3_license_metadata_application.md)

Stage 5U.4 license metadata package verification task files:

- [`completed/stage_5u_4_license_metadata_package_verification.md`](completed/stage_5u_4_license_metadata_package_verification.md)

Stage 5V TestPyPI publish source decision task files:

- [`completed/stage_5v_testpypi_publish_preparation.md`](completed/stage_5v_testpypi_publish_preparation.md)

Stage 5U.5 RC2 tag plan task files:

- [`completed/stage_5u_5_rc2_tag_plan.md`](completed/stage_5u_5_rc2_tag_plan.md)

Stage 5U.6 create RC2 tag task files:

- [`completed/stage_5u_6_create_rc2_tag.md`](completed/stage_5u_6_create_rc2_tag.md)

Stage 5U.7 RC2 package artifact verification task files:

- [`completed/stage_5u_7_rc2_package_artifact_verification.md`](completed/stage_5u_7_rc2_package_artifact_verification.md)

Stage 5U.8 RC2 isolated install smoke task files:

- [`completed/stage_5u_8_rc2_isolated_install_smoke.md`](completed/stage_5u_8_rc2_isolated_install_smoke.md)

Stage 5V.1 TestPyPI name and auth preparation task files:

- [`completed/stage_5v_1_testpypi_name_auth_preparation.md`](completed/stage_5v_1_testpypi_name_auth_preparation.md)

Stage 5V.2 TestPyPI Trusted Publishing setup task files:

- [`completed/stage_5v_2_testpypi_trusted_publishing_setup.md`](completed/stage_5v_2_testpypi_trusted_publishing_setup.md)

Stage 5V.3 TestPyPI Trusted Publisher registration task files:

- [`completed/stage_5v_3_testpypi_trusted_publisher_registration.md`](completed/stage_5v_3_testpypi_trusted_publisher_registration.md)

Stage 5V.4 TestPyPI workflow publish task files:

- [`completed/stage_5v_4_testpypi_workflow_publish.md`](completed/stage_5v_4_testpypi_workflow_publish.md)

Stage 5V.5 TestPyPI install smoke task files:

- [`completed/stage_5v_5_testpypi_install_smoke.md`](completed/stage_5v_5_testpypi_install_smoke.md)

Stage 5W.0.1 create stable tag v0.1.0 task files:

- [`completed/stage_5w_0_1_create_stable_tag_v0_1_0.md`](completed/stage_5w_0_1_create_stable_tag_v0_1_0.md)

Stage 5W.0.2 stable tag package artifact verification task files:

- [`completed/stage_5w_0_2_stable_tag_package_artifact_verification.md`](completed/stage_5w_0_2_stable_tag_package_artifact_verification.md)

Stage 5W.0.3 stable tag isolated install smoke task files:

- [`completed/stage_5w_0_3_stable_tag_isolated_install_smoke.md`](completed/stage_5w_0_3_stable_tag_isolated_install_smoke.md)

Stage 5W.2 PyPI Trusted Publisher registration task files:

- [`completed/stage_5w_2_pypi_trusted_publisher_registration.md`](completed/stage_5w_2_pypi_trusted_publisher_registration.md)

Stage 5W.3 PyPI workflow publish task files:

- [`completed/stage_5w_3_pypi_workflow_publish.md`](completed/stage_5w_3_pypi_workflow_publish.md)

Stage 5W.4 PyPI install smoke task files:

- [`completed/stage_5w_4_pypi_install_smoke.md`](completed/stage_5w_4_pypi_install_smoke.md)

Stage 5X GitHub Release or release-chain closeout decision task files:

- [`completed/stage_5x_github_release_or_release_chain_closeout_decision.md`](completed/stage_5x_github_release_or_release_chain_closeout_decision.md)

Stage 5X.1 GitHub Release creation task files:

- [`completed/stage_5x_1_github_release_creation.md`](completed/stage_5x_1_github_release_creation.md)

Stage 5Q.3 release candidate checklist decision task files:

- [`completed/stage_5q_3_release_candidate_checklist_decision.md`](completed/stage_5q_3_release_candidate_checklist_decision.md)

Stage 5Q.2 privacy / deferred areas audit task files:

- [`completed/stage_5q_2_privacy_deferred_areas_audit.md`](completed/stage_5q_2_privacy_deferred_areas_audit.md)

Stage 5Q.1 packaging metadata / dependency readiness task files:

- [`completed/stage_5q_1_packaging_metadata_dependency_readiness.md`](completed/stage_5q_1_packaging_metadata_dependency_readiness.md)

Stage 5Q.0 public docs / CLI alignment task files:

- [`completed/stage_5q_0_public_docs_cli_alignment.md`](completed/stage_5q_0_public_docs_cli_alignment.md)

Stage 5P.2 target identity history duplicate observation remediation task files:

- [`completed/stage_5p_2_target_identity_history_duplicate_observation_remediation.md`](completed/stage_5p_2_target_identity_history_duplicate_observation_remediation.md)

Stage 5P.1 Ruff formatting remediation task files:

- [`completed/stage_5p_1_ruff_formatting_remediation.md`](completed/stage_5p_1_ruff_formatting_remediation.md)

Stage 5P post-refactor full verification task files:

- [`completed/stage_5p_post_refactor_full_verification.md`](completed/stage_5p_post_refactor_full_verification.md)

Stage 5O.14 test suite component split task files:

- [`completed/stage_5o_14_test_suite_component_split.md`](completed/stage_5o_14_test_suite_component_split.md)

Stage 5O.13 storage compatibility guardrails task files:

- [`completed/stage_5o_13_storage_compatibility_guardrails.md`](completed/stage_5o_13_storage_compatibility_guardrails.md)

Stage 5O.12 context sync dependency extraction task files:

- [`completed/stage_5o_12_context_sync_dependency_extraction.md`](completed/stage_5o_12_context_sync_dependency_extraction.md)

Stage 5O.11 context sync dependency precheck task files:

- [`completed/stage_5o_11_context_sync_dependency_precheck.md`](completed/stage_5o_11_context_sync_dependency_precheck.md)

Stage 5O.9 file writer state boundary task files:

- [`completed/stage_5o_9_file_writer_state_boundary.md`](completed/stage_5o_9_file_writer_state_boundary.md)

Stage 5O.8 discussion builder split task files:

- [`completed/stage_5o_8_discussion_builder_split.md`](completed/stage_5o_8_discussion_builder_split.md)

Stage 5O.7 CLI option boundary task files:

- [`completed/stage_5o_7_cli_option_boundary.md`](completed/stage_5o_7_cli_option_boundary.md)

Stage 5O.6 DB export run coordinator extraction task files:

- [`completed/stage_5o_6_db_export_run_coordinator_extraction.md`](completed/stage_5o_6_db_export_run_coordinator_extraction.md)

Stage 5O.5 DB export run lifecycle characterization task files:

- [`completed/stage_5o_5_db_export_run_lifecycle_characterization.md`](completed/stage_5o_5_db_export_run_lifecycle_characterization.md)

Stage 5O.4 dataset contract constants task files:

- [`completed/stage_5o_4_dataset_contract_constants.md`](completed/stage_5o_4_dataset_contract_constants.md)

Stage 5O.3 CLI parser media size error task files:

- [`completed/stage_5o_3_cli_parser_media_size_error.md`](completed/stage_5o_3_cli_parser_media_size_error.md)

Stage 5O.2 i18n parity guard task files:

- [`completed/stage_5o_2_i18n_parity_guard.md`](completed/stage_5o_2_i18n_parity_guard.md)

Stage 5O.1 config loading source cleanup task files:

- [`completed/stage_5o_1_config_loading_source_cleanup.md`](completed/stage_5o_1_config_loading_source_cleanup.md)

Stage 5O.0 refactoring guardrails task files:

- [`completed/stage_5o_0_refactoring_guardrails.md`](completed/stage_5o_0_refactoring_guardrails.md)

Stage 5N.1 target names history CLI task files:

- [`completed/stage_5n_1_target_names_history_cli.md`](completed/stage_5n_1_target_names_history_cli.md)

Stage 5N.0 target names history read model task files:

- [`completed/stage_5n_0_target_names_history_read_model.md`](completed/stage_5n_0_target_names_history_read_model.md)

Stage 5M.6 operational risk notes task files:

- [`completed/stage_5m_6_operational_risk_notes.md`](completed/stage_5m_6_operational_risk_notes.md)

Stage 5M.5 deferred contract coverage prioritization task files:

- [`completed/stage_5m_5_deferred_contract_coverage_prioritization.md`](completed/stage_5m_5_deferred_contract_coverage_prioritization.md)

Stage 5M.3 schedule / limit / entrypoint UX audit task files:

- [`completed/stage_5m_3_schedule_limit_entrypoint_ux_audit.md`](completed/stage_5m_3_schedule_limit_entrypoint_ux_audit.md)

Stage 5M.2 public docs feature status alignment task files:

- [`completed/stage_5m_2_public_docs_feature_status_alignment.md`](completed/stage_5m_2_public_docs_feature_status_alignment.md)

Stage 5M.0 external risk audit verification task files:

- [`completed/stage_5m_0_external_risk_audit_verification.md`](completed/stage_5m_0_external_risk_audit_verification.md)

Stage 5L.1 release candidate decision recheck task files:

- [`completed/stage_5l_1_release_candidate_decision_recheck.md`](completed/stage_5l_1_release_candidate_decision_recheck.md)

Stage 5K.4 release candidate decision report task files:

- [`completed/stage_5k_4_release_candidate_decision_report.md`](completed/stage_5k_4_release_candidate_decision_report.md)

Stage 5K.3 local verification matrix task files:

- [`completed/stage_5k_3_local_verification_matrix.md`](completed/stage_5k_3_local_verification_matrix.md)

Stage 5K.2 documentation / privacy / changelog release audit task files:

- [`completed/stage_5k_2_documentation_privacy_changelog_release_audit.md`](completed/stage_5k_2_documentation_privacy_changelog_release_audit.md)

Stage 5K.1 packaging metadata readiness audit task files:

- [`completed/stage_5k_1_packaging_metadata_readiness_audit.md`](completed/stage_5k_1_packaging_metadata_readiness_audit.md)

Stage 5K.0 release checklist scope / no-publish boundary task files:

- [`completed/stage_5k_0_release_checklist_scope_no_publish_boundary.md`](completed/stage_5k_0_release_checklist_scope_no_publish_boundary.md)

Stage 5J.3 release readiness recheck / changelog finalization task files:

- [`completed/stage_5j_3_release_readiness_recheck_changelog_finalization.md`](completed/stage_5j_3_release_readiness_recheck_changelog_finalization.md)

Stage 5J.2 fixture-to-contract verification task files:

- [`completed/stage_5j_2_fixture_to_contract_verification.md`](completed/stage_5j_2_fixture_to_contract_verification.md)

Stage 5J.1 non-channel contract tests implementation task files:

- [`completed/stage_5j_1_non_channel_contract_tests_implementation.md`](completed/stage_5j_1_non_channel_contract_tests_implementation.md)

Stage 5J.0 post-5I consistency audit task files:

- [`completed/stage_5j_0_post_5i_consistency_audit.md`](completed/stage_5j_0_post_5i_consistency_audit.md)

Stage 5I.3 non-channel export contract v1 draft task files:

- [`completed/stage_5i_3_non_channel_export_contract_v1_draft.md`](completed/stage_5i_3_non_channel_export_contract_v1_draft.md)

Stage 5I.2 non-channel contract test plan task files:

- [`completed/stage_5i_2_non_channel_contract_test_plan.md`](completed/stage_5i_2_non_channel_contract_test_plan.md)

Stage 5I.1 user/db export synthetic fixture implementation task files:

- [`completed/stage_5i_1_user_db_export_synthetic_fixture_implementation.md`](completed/stage_5i_1_user_db_export_synthetic_fixture_implementation.md)

Stage 5I.0 non-channel synthetic fixtures stage files task files:

- [`completed/stage_5i_0_non_channel_synthetic_fixtures_stage_files.md`](completed/stage_5i_0_non_channel_synthetic_fixtures_stage_files.md)

Stage 5H.3 private archive contract deferred decision task files:

- [`completed/stage_5h_3_private_archive_contract_deferred_decision.md`](completed/stage_5h_3_private_archive_contract_deferred_decision.md)

Stage 5H.2 user + DB export synthetic fixtures plan task files:

- [`completed/stage_5h_2_user_db_export_synthetic_fixtures_plan.md`](completed/stage_5h_2_user_db_export_synthetic_fixtures_plan.md)

Stage 5H.1 non-channel export contract design precheck task files:

- [`completed/stage_5h_1_non_channel_export_contract_design_precheck.md`](completed/stage_5h_1_non_channel_export_contract_design_precheck.md)

Stage 5H.0 changelog / release notes refresh precheck task files:

- [`completed/stage_5h_0_changelog_release_notes_refresh_precheck.md`](completed/stage_5h_0_changelog_release_notes_refresh_precheck.md)

Stage 5G.3 user-facing release readiness audit task files:

- [`completed/stage_5g_3_user_facing_release_readiness_audit.md`](completed/stage_5g_3_user_facing_release_readiness_audit.md)

Stage 5G.2 non-channel dataset contract precheck task files:

- [`completed/stage_5g_2_non_channel_dataset_contract_precheck.md`](completed/stage_5g_2_non_channel_dataset_contract_precheck.md)

Stage 5G.1 synthetic examples regression check task files:

- [`completed/stage_5g_1_synthetic_examples_regression_check.md`](completed/stage_5g_1_synthetic_examples_regression_check.md)

Stage 5G.0 post-5F documentation / examples consistency audit task files:

- [`completed/stage_5g_0_post_5f_documentation_examples_consistency_audit.md`](completed/stage_5g_0_post_5f_documentation_examples_consistency_audit.md)

Stage 5F.5 static dataset summary report design task files:

- [`completed/stage_5f_5_static_dataset_summary_report_design.md`](completed/stage_5f_5_static_dataset_summary_report_design.md)

Stage 5F.4 post-processing example catalogue refinement task files:

- [`completed/stage_5f_4_post_processing_example_catalogue_refinement.md`](completed/stage_5f_4_post_processing_example_catalogue_refinement.md)

Stage 5F.3 dataset doctor output examples task files:

- [`completed/stage_5f_3_dataset_doctor_output_examples.md`](completed/stage_5f_3_dataset_doctor_output_examples.md)

Stage 5F.2 synthetic channel dataset example task files:

- [`completed/stage_5f_2_synthetic_channel_dataset_example.md`](completed/stage_5f_2_synthetic_channel_dataset_example.md)

Stage 5F.1 user documentation navigation audit / quickstart consolidation task files:

- [`completed/stage_5f_1_user_documentation_navigation_audit_quickstart_consolidation.md`](completed/stage_5f_1_user_documentation_navigation_audit_quickstart_consolidation.md)

Stage 5F.0 current architecture / context refresh task files:

- [`completed/stage_5f_0_current_architecture_context_refresh.md`](completed/stage_5f_0_current_architecture_context_refresh.md)

Stage 5E.2 SQLite schema split regression expansion task files:

- [`completed/stage_5e_2_sqlite_schema_split_regression_expansion.md`](completed/stage_5e_2_sqlite_schema_split_regression_expansion.md)

Stage 5E.1 SQLite schema split stage 2 migration helper extraction task files:

- [`completed/stage_5e_1_sqlite_schema_split_stage_2_migration_helper_extraction.md`](completed/stage_5e_1_sqlite_schema_split_stage_2_migration_helper_extraction.md)

Stage 5E.0 SQLite schema split stage 2 migration helpers precheck task files:

- [`completed/stage_5e_0_sqlite_schema_split_stage_2_migration_helpers_precheck.md`](completed/stage_5e_0_sqlite_schema_split_stage_2_migration_helpers_precheck.md)

Stage 5D.5 user quickstart safe first export guide task files:

- [`completed/stage_5d_5_user_quickstart_safe_first_export_guide.md`](completed/stage_5d_5_user_quickstart_safe_first_export_guide.md)

Stage 5D.4 channel export mode matrix tests task files:

- [`completed/stage_5d_4_channel_export_mode_matrix_tests.md`](completed/stage_5d_4_channel_export_mode_matrix_tests.md)

Stage 5D.3 TXT projection contract clarification task files:

- [`completed/stage_5d_3_txt_projection_contract_clarification.md`](completed/stage_5d_3_txt_projection_contract_clarification.md)

Stage 5D.2 run changelog key set contract tests task files:

- [`completed/stage_5d_2_run_changelog_key_set_contract_tests.md`](completed/stage_5d_2_run_changelog_key_set_contract_tests.md)

Stage 5D.1 dataset contract gap closure plan task files:

- [`completed/stage_5d_1_dataset_contract_gap_closure_plan.md`](completed/stage_5d_1_dataset_contract_gap_closure_plan.md)

Stage 5D.0 SQLite schema split stage 1 task files:

- [`completed/stage_5d_0_sqlite_schema_split_stage_1.md`](completed/stage_5d_0_sqlite_schema_split_stage_1.md)

Stage 5C.5 package identity / version policy cleanup task files:

- [`completed/stage_5c_5_package_identity_version_policy_cleanup.md`](completed/stage_5c_5_package_identity_version_policy_cleanup.md)

Stage 5C.4 privacy and sensitive artifacts guide task files:

- [`completed/stage_5c_4_privacy_sensitive_artifacts_guide.md`](completed/stage_5c_4_privacy_sensitive_artifacts_guide.md)

Stage 5C.3 CLI / README / COMMANDS parity audit task files:

- [`completed/stage_5c_3_cli_readme_commands_parity_audit.md`](completed/stage_5c_3_cli_readme_commands_parity_audit.md)

Stage 5C.2 skill routing fallback verification task files:

- [`completed/stage_5c_2_skill_routing_fallback_verification_report.md`](completed/stage_5c_2_skill_routing_fallback_verification_report.md)

Stage 5C.0 dataset contract coverage matrix task files:

- [`completed/stage_5c_0_dataset_contract_coverage_matrix.md`](completed/stage_5c_0_dataset_contract_coverage_matrix.md)

Stage 5C.1 pytest collection hygiene task files:

- [`completed/stage_5c_1_pytest_collection_hygiene.md`](completed/stage_5c_1_pytest_collection_hygiene.md)

Stage 5B.5 SQLite schema decomposition plan task files:

- [`completed/stage_5b_5_sqlite_schema_decomposition_plan.md`](completed/stage_5b_5_sqlite_schema_decomposition_plan.md)

Stage 5B.4 SQLite write queue backpressure task files:

- [`completed/stage_5b_4_sqlite_write_queue_backpressure.md`](completed/stage_5b_4_sqlite_write_queue_backpressure.md)

Stage 5B.3 DB export memory boundaries task files:

- [`completed/stage_5b_3_db_export_memory_boundaries.md`](completed/stage_5b_3_db_export_memory_boundaries.md)

Stage 5B.2 channel export post buffer boundaries task files:

- [`completed/stage_5b_2_channel_export_post_buffer_boundaries.md`](completed/stage_5b_2_channel_export_post_buffer_boundaries.md)

Stage 5B.1 private archive batched storage flush task files:

- [`completed/stage_5b_1_private_archive_batched_storage_flush.md`](completed/stage_5b_1_private_archive_batched_storage_flush.md)

Stage 5B.0 scalability baseline before growth hardening task files:

- [`completed/stage_5b_0_scalability_baseline_before_growth_hardening.md`](completed/stage_5b_0_scalability_baseline_before_growth_hardening.md)

Stage 5A.0 external post-processing boundary skeleton task files:

- [`completed/stage_5a_0_external_post_processing_boundary_skeleton.md`](completed/stage_5a_0_external_post_processing_boundary_skeleton.md)

Stage 4D.2 read-only dataset doctor task files:

- [`completed/stage_4d_2_read_only_dataset_doctor.md`](completed/stage_4d_2_read_only_dataset_doctor.md)

Stage 4D.1 dataset validation contract alignment task files:

- [`completed/stage_4d_1_dataset_validation_contract_alignment.md`](completed/stage_4d_1_dataset_validation_contract_alignment.md)

Stage 4D.0 dataset contract v1 design task files:

- [`completed/stage_4d_0_dataset_contract_v1_design.md`](completed/stage_4d_0_dataset_contract_v1_design.md)

Stage 4C.1 architecture rules sync task files:

- [`completed/stage_4c_1_architecture_rules_sync_after_audit.md`](completed/stage_4c_1_architecture_rules_sync_after_audit.md)

Stage 4C.0 architecture stabilization audit task files:

- [`completed/stage_4c_0_architecture_stabilization_audit_before_expansion.md`](completed/stage_4c_0_architecture_stabilization_audit_before_expansion.md)

Stage 4C.0C completed task files:

- [`completed/stage_4c_0c_test_layout_grouping.md`](completed/stage_4c_0c_test_layout_grouping.md)

Stage 4C.0B completed task files:

- [`completed/stage_4c_0b_channel_export_workflow_split.md`](completed/stage_4c_0b_channel_export_workflow_split.md)

Stage 4B.3 completed task files:

- [`completed/stage_4b_3_run_changelog_artifact.md`](completed/stage_4b_3_run_changelog_artifact.md)

Stage 4B.2 completed task files:

- [`completed/stage_4b_2_dataset_validation_hardening.md`](completed/stage_4b_2_dataset_validation_hardening.md)

Stage 4B.1 completed task files:

- [`completed/stage_4b_1_dataset_integrity_audit_only.md`](completed/stage_4b_1_dataset_integrity_audit_only.md)

Stage 4A.7 completed task files:

- [`completed/stage_4a_7_db_export_txt_profile_parity.md`](completed/stage_4a_7_db_export_txt_profile_parity.md)

Stage 4A.8 completed task files:

- [`completed/stage_4a_8_discussion_export_policy_hardening.md`](completed/stage_4a_8_discussion_export_policy_hardening.md)

Stage 4B.0 completed task files:

- [`completed/stage_4b_0_console_utility_visual_refresh.md`](completed/stage_4b_0_console_utility_visual_refresh.md)

Stage 4A.6 completed task files:

- [`completed/stage_4a_6_context_group_id_fallback_hardening.md`](completed/stage_4a_6_context_group_id_fallback_hardening.md)

Stage 4A.5 completed task files:

- [`completed/stage_4a_5_0_txt_rendering_contract.md`](completed/stage_4a_5_0_txt_rendering_contract.md)
- [`completed/stage_4a_5_1_rendering_models_and_legacy_profile.md`](completed/stage_4a_5_1_rendering_models_and_legacy_profile.md)
- [`completed/stage_4a_5_2_context_readable_renderer.md`](completed/stage_4a_5_2_context_readable_renderer.md)
- [`completed/stage_4a_5_3_export_cli_and_menu_integration.md`](completed/stage_4a_5_3_export_cli_and_menu_integration.md)
- [`completed/stage_4a_5_4_docs_tests_report_lifecycle.md`](completed/stage_4a_5_4_docs_tests_report_lifecycle.md)

Stage 4A completed task files:

- [`completed/stage_4a_0_dataset_validation_architecture_contract.md`](completed/stage_4a_0_dataset_validation_architecture_contract.md)
- [`completed/stage_4a_1_jsonl_manifest_state_validators.md`](completed/stage_4a_1_jsonl_manifest_state_validators.md)
- [`completed/stage_4a_2_media_discussion_validators.md`](completed/stage_4a_2_media_discussion_validators.md)
- [`completed/stage_4a_3_cli_report_renderers.md`](completed/stage_4a_3_cli_report_renderers.md)
- [`completed/stage_4a_4_contract_fixtures_docs_report.md`](completed/stage_4a_4_contract_fixtures_docs_report.md)

Stage 3E.4 completed task files:

- [`completed/stage_3e_4_media_filename_extension_detection_hardening.md`](completed/stage_3e_4_media_filename_extension_detection_hardening.md)

Stage 3E.5 completed task files:

- [`completed/stage_3e_5_interactive_channel_export_options_parity.md`](completed/stage_3e_5_interactive_channel_export_options_parity.md)

Stage 3D.0 completed task files:

- [`completed/stage_3d_0_1_documentation_audit.md`](completed/stage_3d_0_1_documentation_audit.md)
- [`completed/stage_3d_0_2_target_structure_and_migration_plan.md`](completed/stage_3d_0_2_target_structure_and_migration_plan.md)
- [`completed/stage_3d_0_3_move_and_normalize_documentation.md`](completed/stage_3d_0_3_move_and_normalize_documentation.md)
- [`completed/stage_3d_0_4_documentation_indexes_and_navigation.md`](completed/stage_3d_0_4_documentation_indexes_and_navigation.md)
- [`completed/stage_3d_0_5_agents_md_rewrite.md`](completed/stage_3d_0_5_agents_md_rewrite.md)
- [`completed/stage_3d_0_6_root_readme_commands_changelog_alignment.md`](completed/stage_3d_0_6_root_readme_commands_changelog_alignment.md)
- [`completed/stage_3d_0_7_verification_and_governance_report.md`](completed/stage_3d_0_7_verification_and_governance_report.md)

Stage 3D.1 completed task files:

- [`completed/stage_3d_1_stage_lifecycle_cleanup.md`](completed/stage_3d_1_stage_lifecycle_cleanup.md)

Stage 3E.0 completed task files:

- [`completed/stage_3e_0_channel_export_service_decomposition.md`](completed/stage_3e_0_channel_export_service_decomposition.md)

Stage 3E.1 completed task files:

- [`completed/stage_3e_1_dataset_atomic_write_commit_safety.md`](completed/stage_3e_1_dataset_atomic_write_commit_safety.md)

Stage 3E.2 completed task files:

- [`completed/stage_3e_2_dataset_schema_contract_tests.md`](completed/stage_3e_2_dataset_schema_contract_tests.md)

Stage 3E.3 completed task files:

- [`completed/stage_3e_3_state_consistency_hardening.md`](completed/stage_3e_3_state_consistency_hardening.md)

Archived launch prompts and prompt packs:

- [`../archive/old_prompts/stage_3d_0_general_prompt.md`](../archive/old_prompts/stage_3d_0_general_prompt.md)
- [`../archive/old_prompts/post_stage_3c_hardening_codex_pack.zip`](../archive/old_prompts/post_stage_3c_hardening_codex_pack.zip)

## Reports

Reports under [`reports/`](reports/) are factual completion records. They can contain time-bound claims that were true for a specific stage.

Current Stage 3D.0, Stage 3D.1, Stage 3E.0, Stage 3E.1, Stage 3E.2, Stage 3E.3, Stage 3E.4, Stage 3E.5, Stage 4A, Stage 4A.5, Stage 4A.6, Stage 4A.7, Stage 4A.8, Stage 4B.1, Stage 4B.2, Stage 4B.3, Stage 4C.0, Stage 4C.0B, and Stage 4C.0C records:

- [`reports/STAGE_3D_0_1_DOCUMENTATION_AUDIT.md`](reports/STAGE_3D_0_1_DOCUMENTATION_AUDIT.md)
- [`reports/STAGE_3D_0_2_TARGET_DOCS_STRUCTURE_PLAN.md`](reports/STAGE_3D_0_2_TARGET_DOCS_STRUCTURE_PLAN.md)
- [`reports/STAGE_3D_0_3_DOCS_MIGRATION_REPORT.md`](reports/STAGE_3D_0_3_DOCS_MIGRATION_REPORT.md)
- [`reports/STAGE_3D_0_4_DOCS_INDEXES_REPORT.md`](reports/STAGE_3D_0_4_DOCS_INDEXES_REPORT.md)
- [`reports/STAGE_3D_0_5_AGENTS_REWRITE_REPORT.md`](reports/STAGE_3D_0_5_AGENTS_REWRITE_REPORT.md)
- [`reports/STAGE_3D_0_6_ROOT_DOCS_ALIGNMENT_REPORT.md`](reports/STAGE_3D_0_6_ROOT_DOCS_ALIGNMENT_REPORT.md)
- [`reports/STAGE_3D_0_PROJECT_GOVERNANCE_DOCS_REORGANIZATION_REPORT.md`](reports/STAGE_3D_0_PROJECT_GOVERNANCE_DOCS_REORGANIZATION_REPORT.md)
- [`reports/STAGE_3D_1_STAGE_LIFECYCLE_CLEANUP_REPORT.md`](reports/STAGE_3D_1_STAGE_LIFECYCLE_CLEANUP_REPORT.md)
- [`reports/STAGE_3E_0_CHANNEL_EXPORT_SERVICE_DECOMPOSITION_REPORT.md`](reports/STAGE_3E_0_CHANNEL_EXPORT_SERVICE_DECOMPOSITION_REPORT.md)
- [`reports/STAGE_3E_1_DATASET_ATOMIC_WRITE_COMMIT_SAFETY_REPORT.md`](reports/STAGE_3E_1_DATASET_ATOMIC_WRITE_COMMIT_SAFETY_REPORT.md)
- [`reports/STAGE_3E_2_DATASET_SCHEMA_CONTRACT_TESTS_REPORT.md`](reports/STAGE_3E_2_DATASET_SCHEMA_CONTRACT_TESTS_REPORT.md)
- [`reports/STAGE_3E_3_STATE_CONSISTENCY_HARDENING_REPORT.md`](reports/STAGE_3E_3_STATE_CONSISTENCY_HARDENING_REPORT.md)
- [`reports/STAGE_3E_4_MEDIA_FILENAME_EXTENSION_DETECTION_HARDENING_REPORT.md`](reports/STAGE_3E_4_MEDIA_FILENAME_EXTENSION_DETECTION_HARDENING_REPORT.md)
- [`reports/STAGE_3E_5_INTERACTIVE_CHANNEL_EXPORT_OPTIONS_PARITY_REPORT.md`](reports/STAGE_3E_5_INTERACTIVE_CHANNEL_EXPORT_OPTIONS_PARITY_REPORT.md)
- [`reports/STAGE_4A_DATASET_VALIDATION_INSPECTION_REPORT.md`](reports/STAGE_4A_DATASET_VALIDATION_INSPECTION_REPORT.md)
- [`reports/STAGE_4A_5_CONTEXT_READABLE_TXT_PROFILE_REPORT.md`](reports/STAGE_4A_5_CONTEXT_READABLE_TXT_PROFILE_REPORT.md)
- [`reports/STAGE_4A_6_CONTEXT_GROUP_ID_FALLBACK_HARDENING_REPORT.md`](reports/STAGE_4A_6_CONTEXT_GROUP_ID_FALLBACK_HARDENING_REPORT.md)
- [`reports/STAGE_4A_7_DB_EXPORT_TXT_PROFILE_PARITY_REPORT.md`](reports/STAGE_4A_7_DB_EXPORT_TXT_PROFILE_PARITY_REPORT.md)
- [`reports/STAGE_4A_8_DISCUSSION_EXPORT_POLICY_HARDENING_REPORT.md`](reports/STAGE_4A_8_DISCUSSION_EXPORT_POLICY_HARDENING_REPORT.md)
- [`reports/STAGE_4B_0_CONSOLE_UTILITY_VISUAL_REFRESH_REPORT.md`](reports/STAGE_4B_0_CONSOLE_UTILITY_VISUAL_REFRESH_REPORT.md)
- [`reports/STAGE_4B_1_DATASET_INTEGRITY_AUDIT_REPORT.md`](reports/STAGE_4B_1_DATASET_INTEGRITY_AUDIT_REPORT.md)
- [`reports/STAGE_4B_2_DATASET_VALIDATION_HARDENING_REPORT.md`](reports/STAGE_4B_2_DATASET_VALIDATION_HARDENING_REPORT.md)
- [`reports/STAGE_4B_3_RUN_CHANGELOG_ARTIFACT_REPORT.md`](reports/STAGE_4B_3_RUN_CHANGELOG_ARTIFACT_REPORT.md)
- [`reports/STAGE_4C_0_ARCHITECTURE_STABILIZATION_AUDIT_BEFORE_EXPANSION_REPORT.md`](reports/STAGE_4C_0_ARCHITECTURE_STABILIZATION_AUDIT_BEFORE_EXPANSION_REPORT.md)
- [`reports/STAGE_4C_0_STRUCTURAL_DECOMPOSITION_REPORT.md`](reports/STAGE_4C_0_STRUCTURAL_DECOMPOSITION_REPORT.md)
- [`reports/STAGE_4C_0B_CHANNEL_EXPORT_WORKFLOW_SPLIT_REPORT.md`](reports/STAGE_4C_0B_CHANNEL_EXPORT_WORKFLOW_SPLIT_REPORT.md)
- [`reports/STAGE_4C_0C_TEST_LAYOUT_GROUPING_REPORT.md`](reports/STAGE_4C_0C_TEST_LAYOUT_GROUPING_REPORT.md)
- [`reports/STAGE_4C_1_ARCHITECTURE_RULES_SYNC_AFTER_AUDIT_REPORT.md`](reports/STAGE_4C_1_ARCHITECTURE_RULES_SYNC_AFTER_AUDIT_REPORT.md)
- [`reports/STAGE_4D_0_DATASET_CONTRACT_V1_DESIGN_REPORT.md`](reports/STAGE_4D_0_DATASET_CONTRACT_V1_DESIGN_REPORT.md)
- [`reports/STAGE_4D_1_DATASET_VALIDATION_CONTRACT_ALIGNMENT_REPORT.md`](reports/STAGE_4D_1_DATASET_VALIDATION_CONTRACT_ALIGNMENT_REPORT.md)
- [`reports/STAGE_4D_2_READ_ONLY_DATASET_DOCTOR_REPORT.md`](reports/STAGE_4D_2_READ_ONLY_DATASET_DOCTOR_REPORT.md)
- [`reports/STAGE_5A_0_EXTERNAL_POST_PROCESSING_BOUNDARY_SKELETON_REPORT.md`](reports/STAGE_5A_0_EXTERNAL_POST_PROCESSING_BOUNDARY_SKELETON_REPORT.md)
- [`reports/STAGE_5B_0_SCALABILITY_BASELINE_REPORT.md`](reports/STAGE_5B_0_SCALABILITY_BASELINE_REPORT.md)
- [`reports/STAGE_5B_1_PRIVATE_ARCHIVE_BATCHED_STORAGE_FLUSH_REPORT.md`](reports/STAGE_5B_1_PRIVATE_ARCHIVE_BATCHED_STORAGE_FLUSH_REPORT.md)
- [`reports/STAGE_5B_2_CHANNEL_EXPORT_POST_BUFFER_BOUNDARIES_REPORT.md`](reports/STAGE_5B_2_CHANNEL_EXPORT_POST_BUFFER_BOUNDARIES_REPORT.md)
- [`reports/STAGE_5B_3_DB_EXPORT_MEMORY_BOUNDARIES_REPORT.md`](reports/STAGE_5B_3_DB_EXPORT_MEMORY_BOUNDARIES_REPORT.md)
- [`reports/STAGE_5B_4_SQLITE_WRITE_QUEUE_BACKPRESSURE_REPORT.md`](reports/STAGE_5B_4_SQLITE_WRITE_QUEUE_BACKPRESSURE_REPORT.md)
- [`reports/STAGE_5B_5_SQLITE_SCHEMA_DECOMPOSITION_PLAN_REPORT.md`](reports/STAGE_5B_5_SQLITE_SCHEMA_DECOMPOSITION_PLAN_REPORT.md)
- [`reports/STAGE_5C_0_DATASET_CONTRACT_COVERAGE_MATRIX_REPORT.md`](reports/STAGE_5C_0_DATASET_CONTRACT_COVERAGE_MATRIX_REPORT.md)
- [`reports/STAGE_5C_1_PYTEST_COLLECTION_HYGIENE_REPORT.md`](reports/STAGE_5C_1_PYTEST_COLLECTION_HYGIENE_REPORT.md)
- [`reports/STAGE_5C_2_SKILL_ROUTING_FALLBACK_VERIFICATION_REPORT.md`](reports/STAGE_5C_2_SKILL_ROUTING_FALLBACK_VERIFICATION_REPORT.md)
- [`reports/STAGE_5C_3_CLI_README_COMMANDS_PARITY_AUDIT_REPORT.md`](reports/STAGE_5C_3_CLI_README_COMMANDS_PARITY_AUDIT_REPORT.md)
- [`reports/STAGE_5C_4_PRIVACY_SENSITIVE_ARTIFACTS_GUIDE_REPORT.md`](reports/STAGE_5C_4_PRIVACY_SENSITIVE_ARTIFACTS_GUIDE_REPORT.md)
- [`reports/STAGE_5C_5_PACKAGE_IDENTITY_VERSION_POLICY_CLEANUP_REPORT.md`](reports/STAGE_5C_5_PACKAGE_IDENTITY_VERSION_POLICY_CLEANUP_REPORT.md)
- [`reports/STAGE_5D_0_SQLITE_SCHEMA_SPLIT_STAGE_1_REPORT.md`](reports/STAGE_5D_0_SQLITE_SCHEMA_SPLIT_STAGE_1_REPORT.md)
- [`reports/STAGE_5D_1_DATASET_CONTRACT_GAP_CLOSURE_PLAN_REPORT.md`](reports/STAGE_5D_1_DATASET_CONTRACT_GAP_CLOSURE_PLAN_REPORT.md)
- [`reports/STAGE_5D_2_RUN_CHANGELOG_KEY_SET_CONTRACT_TESTS_REPORT.md`](reports/STAGE_5D_2_RUN_CHANGELOG_KEY_SET_CONTRACT_TESTS_REPORT.md)
- [`reports/STAGE_5D_3_TXT_PROJECTION_CONTRACT_CLARIFICATION_REPORT.md`](reports/STAGE_5D_3_TXT_PROJECTION_CONTRACT_CLARIFICATION_REPORT.md)
- [`reports/STAGE_5D_4_CHANNEL_EXPORT_MODE_MATRIX_TESTS_REPORT.md`](reports/STAGE_5D_4_CHANNEL_EXPORT_MODE_MATRIX_TESTS_REPORT.md)
- [`reports/STAGE_5D_5_USER_QUICKSTART_SAFE_FIRST_EXPORT_GUIDE_REPORT.md`](reports/STAGE_5D_5_USER_QUICKSTART_SAFE_FIRST_EXPORT_GUIDE_REPORT.md)
- [`reports/STAGE_5E_0_SQLITE_SCHEMA_SPLIT_STAGE_2_MIGRATION_HELPERS_PRECHECK_REPORT.md`](reports/STAGE_5E_0_SQLITE_SCHEMA_SPLIT_STAGE_2_MIGRATION_HELPERS_PRECHECK_REPORT.md)
- [`reports/STAGE_5E_1_SQLITE_SCHEMA_SPLIT_STAGE_2_MIGRATION_HELPER_EXTRACTION_REPORT.md`](reports/STAGE_5E_1_SQLITE_SCHEMA_SPLIT_STAGE_2_MIGRATION_HELPER_EXTRACTION_REPORT.md)
- [`reports/STAGE_5E_2_SQLITE_SCHEMA_SPLIT_REGRESSION_EXPANSION_REPORT.md`](reports/STAGE_5E_2_SQLITE_SCHEMA_SPLIT_REGRESSION_EXPANSION_REPORT.md)
- [`reports/STAGE_5F_0_CURRENT_ARCHITECTURE_CONTEXT_REFRESH_REPORT.md`](reports/STAGE_5F_0_CURRENT_ARCHITECTURE_CONTEXT_REFRESH_REPORT.md)

## Stage lifecycle

Stage files move through this lifecycle:

```text
active task -> implementation -> tests/checks -> report -> lifecycle cleanup -> completed task history
```

Active files define executable work. Completed files preserve historical instructions. Reports record what actually happened.

Stage lifecycle cleanup is mandatory after a stage is fully complete and its final report exists:

- Move completed stage task files from [`active/`](active/) to [`completed/`](completed/).
- Move general launch prompts to [`../archive/old_prompts/`](../archive/old_prompts/).
- Update this index.
- Ensure [`active/`](active/) contains only unfinished or next active work.

General prompts and prompt packs usually belong under [`../archive/old_prompts/`](../archive/old_prompts/), not under `active/` or `completed/`.

Do not perform completion cleanup before the final stage report exists.

Before marking a stage complete, confirm the required work is done, required verification is recorded, the stage report exists, relevant docs are current, completed task files have moved to [`completed/`](completed/), launch prompts have moved to [`../archive/old_prompts/`](../archive/old_prompts/), and this index reflects the final stage state.

## Rules for agents

- Read `AGENTS.md` first.
- Execute only the active task requested by the user.
- Do not use completed task files as current instructions.
- Do not treat reports as feature requests.
- Do not use archived prompts or prompt packs as current guidance unless explicitly asked.
- Do not start future roadmap work without an active task.
- Keep docs and reports aligned with the behavior being changed.
