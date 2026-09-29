DROP TABLE IF EXISTS staging_json;

CREATE TEMP TABLE staging_json AS
SELECT
    (elem ->> 0)::int AS id,
    elem ->> 1 AS requester_name,
    elem ->> 2 AS requester_email,
    elem ->> 4 AS request_text,
    elem ->> 5 AS status
FROM (
    SELECT jsonb_array_elements(
        pg_read_file(:'jsonfile')::jsonb -> 'rows'
    ) AS elem
) AS sub;

SELECT COUNT(*) AS total_in_json
FROM staging_json;

SELECT
    (
        SELECT COUNT(*)
        FROM staging_json
    ) AS total_in_json,
    (
        SELECT COUNT(*)
        FROM staging_json AS s
        JOIN playbook_requests AS p
            ON p.id = s.id
        WHERE p.requester_name = s.requester_name
          AND p.requester_email = s.requester_email
          AND p.status = s.status
          AND p.request_text = s.request_text
    ) AS fully_matched;