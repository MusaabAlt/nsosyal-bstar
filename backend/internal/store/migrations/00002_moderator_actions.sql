-- +goose Up

-- What a moderator did with a comment on the panel. The model's own decision
-- stays in moderation_decisions untouched; this table only records people.
--
--   approve         the post is fine (Onayla)
--   hide            hide the post (Gizle)
--   remove          remove the post (Kaldır)
--   queue           send the post to human review (Kuyruğa ekle)
--   false_positive  the model flagged it wrongly (Yanlış pozitif bildir)
--
-- approve, hide and remove resolve a comment; queue and false_positive put it
-- (back) into the pending queue.
CREATE TABLE moderator_actions (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    comment_id  uuid        NOT NULL REFERENCES comments (id) ON DELETE CASCADE,
    action      text        NOT NULL CHECK (action IN ('approve', 'hide', 'remove', 'queue', 'false_positive')),
    -- The panel session that acted; NULL if that session is gone.
    session_id  uuid        REFERENCES sessions (id) ON DELETE SET NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Latest action per comment (queue status) and the history timeline.
CREATE INDEX moderator_actions_comment_idx ON moderator_actions (comment_id, created_at DESC, id DESC);
CREATE INDEX moderator_actions_created_idx ON moderator_actions (created_at DESC, id DESC);

-- +goose Down
DROP TABLE moderator_actions;
