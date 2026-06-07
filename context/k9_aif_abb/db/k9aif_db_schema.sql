-- DROP SCHEMA k9aif;

CREATE SCHEMA k9aif AUTHORIZATION postgres;

-- DROP SEQUENCE k9aif.context_artifacts_artifact_id_seq;

CREATE SEQUENCE k9aif.context_artifacts_artifact_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE k9aif.routing_decisions_decision_id_seq;

CREATE SEQUENCE k9aif.routing_decisions_decision_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE k9aif.session_turns_turn_id_seq;

CREATE SEQUENCE k9aif.session_turns_turn_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;-- k9aif.projects definition

-- Drop table

-- DROP TABLE k9aif.projects;

CREATE TABLE k9aif.projects (
	project_id uuid NOT NULL,
	"name" text NOT NULL,
	description text NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT projects_pkey PRIMARY KEY (project_id)
);


-- k9aif.sessions definition

-- Drop table

-- DROP TABLE k9aif.sessions;

CREATE TABLE k9aif.sessions (
	session_id uuid DEFAULT gen_random_uuid() NOT NULL,
	user_id varchar(255) NOT NULL,
	status varchar(30) DEFAULT 'ACTIVE'::character varying NOT NULL,
	current_dpl_level int4 DEFAULT 1 NOT NULL,
	model_affinity varchar(100) NULL,
	active_prefix_hash text NULL,
	session_summary text NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	last_active timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	closed_at timestamptz NULL,
	CONSTRAINT chk_sessions_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'IDLE'::character varying, 'CLOSED'::character varying, 'ARCHIVED'::character varying])::text[]))),
	CONSTRAINT sessions_current_dpl_level_check CHECK ((current_dpl_level >= 1)),
	CONSTRAINT sessions_pkey PRIMARY KEY (session_id)
);
CREATE INDEX idx_sessions_last_active ON k9aif.sessions USING btree (last_active);
CREATE INDEX idx_sessions_status ON k9aif.sessions USING btree (status);
CREATE INDEX idx_sessions_user_id ON k9aif.sessions USING btree (user_id);


-- k9aif.applications definition

-- Drop table

-- DROP TABLE k9aif.applications;

CREATE TABLE k9aif.applications (
	application_id uuid NOT NULL,
	project_id uuid NOT NULL,
	"name" text NOT NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT applications_pkey PRIMARY KEY (application_id),
	CONSTRAINT applications_project_id_fkey FOREIGN KEY (project_id) REFERENCES k9aif.projects(project_id)
);
CREATE INDEX idx_applications_project_id ON k9aif.applications USING btree (project_id);


-- k9aif.context_artifacts definition

-- Drop table

-- DROP TABLE k9aif.context_artifacts;

CREATE TABLE k9aif.context_artifacts (
	artifact_id bigserial NOT NULL,
	session_id uuid NOT NULL,
	artifact_type varchar(50) NOT NULL,
	content_summary text NULL,
	full_content_pointer text NULL,
	content_hash text NULL,
	cache_eligible bool DEFAULT true NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT context_artifacts_pkey PRIMARY KEY (artifact_id),
	CONSTRAINT context_artifacts_session_id_fkey FOREIGN KEY (session_id) REFERENCES k9aif.sessions(session_id) ON DELETE CASCADE
);
CREATE INDEX idx_context_artifacts_hash ON k9aif.context_artifacts USING btree (content_hash);
CREATE INDEX idx_context_artifacts_session_id ON k9aif.context_artifacts USING btree (session_id);
CREATE INDEX idx_context_artifacts_type ON k9aif.context_artifacts USING btree (artifact_type);


-- k9aif.intake_submission definition

-- Drop table

-- DROP TABLE k9aif.intake_submission;

CREATE TABLE k9aif.intake_submission (
	intake_id uuid NOT NULL,
	project_id uuid NOT NULL,
	application_id uuid NOT NULL,
	engagement_goal varchar(50) NULL,
	status varchar(50) DEFAULT 'draft'::character varying NULL,
	questionnaire_version varchar(20) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp NULL,
	submitted_at timestamp NULL,
	s3_uri text NULL,
	CONSTRAINT intake_submission_pkey PRIMARY KEY (intake_id),
	CONSTRAINT intake_submission_application_id_fkey FOREIGN KEY (application_id) REFERENCES k9aif.applications(application_id),
	CONSTRAINT intake_submission_project_id_fkey FOREIGN KEY (project_id) REFERENCES k9aif.projects(project_id)
);
CREATE INDEX idx_intake_submission_application_id ON k9aif.intake_submission USING btree (application_id);
CREATE INDEX idx_intake_submission_project_id ON k9aif.intake_submission USING btree (project_id);


-- k9aif.session_turns definition

-- Drop table

-- DROP TABLE k9aif.session_turns;

CREATE TABLE k9aif.session_turns (
	turn_id bigserial NOT NULL,
	session_id uuid NOT NULL,
	turn_index int4 NOT NULL,
	"role" varchar(30) NOT NULL,
	"content" text NOT NULL,
	token_count int4 NULL,
	compressed_flag bool DEFAULT false NOT NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT chk_session_turns_role CHECK (((role)::text = ANY ((ARRAY['SYSTEM'::character varying, 'USER'::character varying, 'ASSISTANT'::character varying, 'TOOL'::character varying, 'SUMMARY'::character varying])::text[]))),
	CONSTRAINT session_turns_pkey PRIMARY KEY (turn_id),
	CONSTRAINT uq_session_turns_session_turn UNIQUE (session_id, turn_index),
	CONSTRAINT session_turns_session_id_fkey FOREIGN KEY (session_id) REFERENCES k9aif.sessions(session_id) ON DELETE CASCADE
);
CREATE INDEX idx_session_turns_session_id ON k9aif.session_turns USING btree (session_id);
CREATE INDEX idx_session_turns_session_turn ON k9aif.session_turns USING btree (session_id, turn_index);


-- k9aif.workflow_event definition

-- Drop table

-- DROP TABLE k9aif.workflow_event;

CREATE TABLE k9aif.workflow_event (
	event_id uuid NOT NULL,
	intake_id uuid NOT NULL,
	event_type varchar(50) NULL,
	event_status varchar(50) NULL,
	payload_json jsonb NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT workflow_event_pkey PRIMARY KEY (event_id),
	CONSTRAINT workflow_event_intake_id_fkey FOREIGN KEY (intake_id) REFERENCES k9aif.intake_submission(intake_id)
);
CREATE INDEX idx_workflow_event_intake_id ON k9aif.workflow_event USING btree (intake_id);


-- k9aif.artifact_record definition

-- Drop table

-- DROP TABLE k9aif.artifact_record;

CREATE TABLE k9aif.artifact_record (
	artifact_id uuid NOT NULL,
	intake_id uuid NOT NULL,
	artifact_type varchar(50) NULL,
	storage_uri text NULL,
	status varchar(50) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT artifact_record_pkey PRIMARY KEY (artifact_id),
	CONSTRAINT artifact_record_intake_id_fkey FOREIGN KEY (intake_id) REFERENCES k9aif.intake_submission(intake_id)
);
CREATE INDEX idx_artifact_record_intake_id ON k9aif.artifact_record USING btree (intake_id);


-- k9aif.intake_section definition

-- Drop table

-- DROP TABLE k9aif.intake_section;

CREATE TABLE k9aif.intake_section (
	section_id uuid NOT NULL,
	intake_id uuid NOT NULL,
	section_name varchar(50) NULL,
	section_label varchar(100) NULL,
	"content" text NULL,
	is_mandatory bool DEFAULT true NULL,
	is_completed bool DEFAULT false NULL,
	display_order int4 NULL,
	updated_at timestamp NULL,
	CONSTRAINT intake_section_pkey PRIMARY KEY (section_id),
	CONSTRAINT intake_section_intake_id_fkey FOREIGN KEY (intake_id) REFERENCES k9aif.intake_submission(intake_id)
);
CREATE INDEX idx_intake_section_intake_id ON k9aif.intake_section USING btree (intake_id);


-- k9aif.routing_decisions definition

-- Drop table

-- DROP TABLE k9aif.routing_decisions;

CREATE TABLE k9aif.routing_decisions (
	decision_id bigserial NOT NULL,
	session_id uuid NOT NULL,
	turn_id int8 NULL,
	prompt_hash text NULL,
	selected_model varchar(100) NOT NULL,
	complexity_score numeric(5, 2) NULL,
	governance_score numeric(5, 2) NULL,
	routing_reason text NOT NULL,
	decision_metadata jsonb NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
	CONSTRAINT routing_decisions_pkey PRIMARY KEY (decision_id),
	CONSTRAINT routing_decisions_session_id_fkey FOREIGN KEY (session_id) REFERENCES k9aif.sessions(session_id) ON DELETE CASCADE,
	CONSTRAINT routing_decisions_turn_id_fkey FOREIGN KEY (turn_id) REFERENCES k9aif.session_turns(turn_id) ON DELETE SET NULL
);
CREATE INDEX idx_routing_decisions_created_at ON k9aif.routing_decisions USING btree (created_at);
CREATE INDEX idx_routing_decisions_metadata_gin ON k9aif.routing_decisions USING gin (decision_metadata);
CREATE INDEX idx_routing_decisions_selected_model ON k9aif.routing_decisions USING btree (selected_model);
CREATE INDEX idx_routing_decisions_session_id ON k9aif.routing_decisions USING btree (session_id);