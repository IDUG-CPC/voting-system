


DROP INDEX "SCORE_SESSION_IDX";
DROP INDEX "PRESENTER_TYPE_IDX";
DROP INDEX "SUBJECT_IDX";
DROP INDEX "MODERATOR_IDX";
DROP INDEX "SESSION_IDX";
DROP INDEX "SESSION_PRESENTER_TYPE_IDX";
DROP INDEX "SESSION_SUBJECT_IDX";

DROP VIEW "vote"."VSTATISTICS" ;
DROP VIEW "vote"."VMODAVAIL";
DROP VIEW "vote"."VMODTAKEN" ;
DROP VIEW "vote"."VMODALL" ;
DROP VIEW "vote"."VSESSIONS" ;

DROP VIEW "vote"."BEST_SESSION";
DROP VIEW "vote"."BEST_USER_SESSION";
DROP VIEW "vote"."TRACKS";
DROP VIEW "vote"."MODERATORS";


DROP TABLE "vote"."SCORE";
DROP TABLE "vote"."MODERATOR_THANKYOU";
DROP TABLE "vote"."MODERATOR";
DROP TABLE "vote"."SESSION";
DROP TABLE "vote"."PRESENTER_TYPE";
DROP TABLE "vote"."SUBJECT";

DROP TABLE "vote"."CURRENT_EVENT";

CREATE TABLE "vote"."CURRENT_EVENT" (
    "SESSION_EVENT"   CHARACTER VARYING(10) NOT NULL,
    "EVENT_CITY"      CHARACTER VARYING(30) NOT NULL,
    "EVENT_DATE"      CHARACTER VARYING(30) NOT NULL,
    "IS_ACTIVE"       BOOLEAN NOT NULL DEFAULT FALSE,

    PRIMARY KEY ("SESSION_EVENT")
);


INSERT INTO "vote"."CURRENT_EVENT" ("SESSION_EVENT","EVENT_CITY","EVENT_DATE","IS_ACTIVE") VALUES ('EMEA2025','Dusseldorf','October 26 - 30',TRUE);




CREATE TABLE
    "vote"."PRESENTER_TYPE"
    (
        "PRESENTER_TYPE_CODE"                 CHAR(1) NOT NULL,
        "PRESENTER_TYPE_DESC"             VARCHAR(20),

        primary key ("PRESENTER_TYPE_CODE")
    );

insert into "vote"."PRESENTER_TYPE"("PRESENTER_TYPE_CODE", "PRESENTER_TYPE_DESC") values ('1', 'User/Consultant');
insert into "vote"."PRESENTER_TYPE"("PRESENTER_TYPE_CODE", "PRESENTER_TYPE_DESC") values ('2', 'IBM');
insert into "vote"."PRESENTER_TYPE"("PRESENTER_TYPE_CODE", "PRESENTER_TYPE_DESC") values ('3', 'BMC');
insert into "vote"."PRESENTER_TYPE"("PRESENTER_TYPE_CODE", "PRESENTER_TYPE_DESC") values ('4', 'Broadcom');
insert into "vote"."PRESENTER_TYPE"("PRESENTER_TYPE_CODE", "PRESENTER_TYPE_DESC") values ('5', 'Rocket Software');
insert into "vote"."PRESENTER_TYPE"("PRESENTER_TYPE_CODE", "PRESENTER_TYPE_DESC") values ('6', 'Vendor');


CREATE TABLE
    "vote"."SUBJECT"
    (
        "SUBJECT_ID"                         CHAR(1) NOT NULL,
        "SUBJECT_DESC"                    VARCHAR(15),

        primary key ("SUBJECT_ID")
    );

insert into "vote"."SUBJECT"("SUBJECT_ID", "SUBJECT_DESC") values ('1', 'z/OS');
insert into "vote"."SUBJECT"("SUBJECT_ID", "SUBJECT_DESC") values ('2', 'LUW');
insert into "vote"."SUBJECT"("SUBJECT_ID", "SUBJECT_DESC") values ('3', 'AppDev');
insert into "vote"."SUBJECT"("SUBJECT_ID", "SUBJECT_DESC") values ('4', 'Cross Platform');
insert into "vote"."SUBJECT"("SUBJECT_ID", "SUBJECT_DESC") values ('5', 'AI / ML');



CREATE TABLE
    "vote"."SESSION"
    (
        "SESSION_EVENT"                      CHARACTER VARYING(10) NOT NULL,
        "SESSION_CODE"                       CHARACTER VARYING(5) NOT NULL,
        "SESSION_DATE"                       DATE,
        "SESSION_START"                      TIME,
        "SESSION_END"                        TIME,
        "SESSION_NUMBER"                     CHARACTER VARYING(10),
        "SESSION_TITLE"                      CHARACTER VARYING(250),
        "SUBJECT_ID"                         CHAR(1) NOT NULL,
        "PRIMARY_PRESENTER_FIRSTNAME"        CHARACTER VARYING(50),
        "PRIMARY_PRESENTER_LASTNAME"         CHARACTER VARYING(50),
        "PRIMARY_PRESENTER_COMPANY"          CHARACTER VARYING(50),
        "SECONDARY_PRESENTER_FIRSTNAME"      CHARACTER VARYING(50),
        "SECONDARY_PRESENTER_LASTNAME"       CHARACTER VARYING(50),
        "SECONDARY_PRESENTER_COMPANY"        CHARACTER VARYING(50),
        "PRESENTER_TYPE_CODE"                CHAR(1) NOT NULL,

        "START_COUNT"  INTEGER ,
        "MID_COUNT"    INTEGER ,
        "COMMENTS"    CHARACTER VARYING(400),

        "MODERATOR_STATUS_ID"           SMALLINT NOT NULL DEFAULT 0 ,

        PRIMARY KEY ("SESSION_EVENT", "SESSION_CODE"),
        CONSTRAINT "PRESENTER_TYPE_FKEY" FOREIGN KEY ("PRESENTER_TYPE_CODE") REFERENCES "PRESENTER_TYPE" ("PRESENTER_TYPE_CODE"),
        CONSTRAINT "SUBJECT_FKEY" FOREIGN KEY ("SUBJECT_ID") REFERENCES "SUBJECT" ("SUBJECT_ID")
    );



CREATE TABLE
    "vote"."SCORE"
    (
        "SCORE_ID"          INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
        "SESSION_EVENT"                           CHARACTER VARYING(10) NOT NULL,
        "SESSION_CODE"                       CHARACTER VARYING(5) NOT NULL,
        "OVERALL_SCORE"           INTEGER,
        "SPEAKER_SCORE"           INTEGER,
        "MATERIAL_SCORE"          INTEGER,
        "LEVEL_SCORE"             INTEGER,
        "NOTES"                   CHARACTER VARYING(400),
        "LAST_MODIFIED_BY"        CHARACTER VARYING(20) NOT NULL ,
        "LAST_MODIFIED_TIMESTAMP" TIMESTAMP NOT NULL ,

        PRIMARY KEY ("SCORE_ID"),
        CONSTRAINT "SESSION_FKEY" FOREIGN KEY ("SESSION_EVENT", "SESSION_CODE") REFERENCES "SESSION" ("SESSION_EVENT", "SESSION_CODE")
    );




CREATE TABLE
    "vote"."MODERATOR"
    (
        "SESSION_EVENT"                           CHARACTER VARYING(10) NOT NULL,
        "SESSION_CODE"                       CHARACTER VARYING(5) NOT NULL,
        "MODERATOR_NAME"                        CHARACTER VARYING(100),
        "MODERATOR_EMAIL"                       CHARACTER VARYING(50),

        CONSTRAINT "SESSION_FKEY" FOREIGN KEY ("SESSION_EVENT", "SESSION_CODE") REFERENCES "SESSION" ("SESSION_EVENT", "SESSION_CODE")
    );


CREATE TABLE
    "vote"."MODERATOR_THANKYOU"
    (
        "SESSION_EVENT"     CHARACTER VARYING(10) NOT NULL,
        "MODERATOR_EMAIL"   CHARACTER VARYING(50) NOT NULL,
        "THANK_YOU_SENT"    BOOLEAN NOT NULL DEFAULT FALSE,
        "SENT_AT"           TIMESTAMP,

        PRIMARY KEY ("SESSION_EVENT", "MODERATOR_EMAIL")
    );


CREATE INDEX "SCORE_SESSION_IDX" ON "vote"."SCORE" ("SESSION_EVENT", "SESSION_CODE");
CREATE UNIQUE INDEX "PRESENTER_TYPE_IDX" ON "vote"."PRESENTER_TYPE" ("PRESENTER_TYPE_CODE");
CREATE UNIQUE INDEX "SUBJECT_IDX" ON "vote"."SUBJECT" ("SUBJECT_ID");
CREATE UNIQUE INDEX "MODERATOR_IDX" ON "vote"."MODERATOR" ("SESSION_EVENT", "SESSION_CODE");
CREATE UNIQUE INDEX "SESSION_IDX" ON "vote"."SESSION" ("SESSION_EVENT", "SESSION_CODE");

CREATE INDEX "SESSION_PRESENTER_TYPE_IDX" ON "vote"."SESSION" ("PRESENTER_TYPE_CODE");
CREATE INDEX "SESSION_SUBJECT_IDX" ON "vote"."SESSION" ("SUBJECT_ID");









CREATE VIEW
    "vote"."BEST_USER_SESSION"
    (
        "SESSION_EVENT",
        "SESSION_CODE",
        "PRIMARY_PRESENTER",
        "PRIMARY_PRESENTER_COMPANY",
        "SECONDARY_PRESENTER",
        "SECONDARY_PRESENTER_COMPANY",
        "PRESENTER_TYPE_CODE",
        "RATING",
        "RANK"
    )
    AS
SELECT
    y."SESSION_EVENT"                        AS "SESSION_EVENT",
    y."SESSION_CODE"                        AS "SESSION_CODE",
    e."PRIMARY_PRESENTER_FIRSTNAME" || ' ' || e."PRIMARY_PRESENTER_LASTNAME"          AS "PRIMARY_PRESENTER",
    e."PRIMARY_PRESENTER_COMPANY"            AS "PRIMARY_PRESENTER_COMPANY",
    e."SECONDARY_PRESENTER_FIRSTNAME" || ' ' || e."SECONDARY_PRESENTER_LASTNAME"   AS "SECONDARY_PRESENTER",
    e."SECONDARY_PRESENTER_COMPANY"  AS "SECONDARY_PRESENTER_COMPANY",
    e."PRESENTER_TYPE_CODE"                    AS "PRESENTER_TYPE_CODE",
    y."RATING"                             AS "RATING",
    RANK() OVER (ORDER BY y."RATING" DESC) AS "RANK"
FROM
    (   SELECT
            x."SESSION_EVENT",
            x."SESSION_CODE",
            ROUND(AVG(x."SCORE_TOTAL" / x."SCORE_COUNT"), 2) AS "RATING"
        FROM
            (   SELECT
                    "SESSION_EVENT",
                    "SESSION_CODE",
                    COALESCE("OVERALL_SCORE", 0) + COALESCE("SPEAKER_SCORE", 0) + COALESCE("MATERIAL_SCORE", 0) AS "SCORE_TOTAL",
                    CASE
                        WHEN "OVERALL_SCORE" IS NULL
                        THEN 0
                        ELSE 1
                    END +
                    CASE
                        WHEN "SPEAKER_SCORE" IS NULL
                        THEN 0
                        ELSE 1
                    END +
                    CASE
                        WHEN "MATERIAL_SCORE" IS NULL
                        THEN 0
                        ELSE 1
                    END AS "SCORE_COUNT"
                FROM
                    "vote"."SCORE"
                WHERE
                    COALESCE("OVERALL_SCORE", "SPEAKER_SCORE", "MATERIAL_SCORE") IS NOT NULL) x
        GROUP BY
            x."SESSION_EVENT", x."SESSION_CODE"
        HAVING
            COUNT(*) >= 10  ) y
JOIN "vote"."SESSION" e ON y."SESSION_EVENT" = e."SESSION_EVENT" and y."SESSION_CODE" = e."SESSION_CODE"
INNER JOIN "vote"."PRESENTER_TYPE" p ON e."PRESENTER_TYPE_CODE" = p."PRESENTER_TYPE_CODE"
WHERE p."PRESENTER_TYPE_DESC" = 'User/Consultant';


CREATE VIEW
    "vote"."BEST_SESSION"
    (
        "SESSION_EVENT",
        "SESSION_CODE",
        "PRIMARY_PRESENTER",
        "PRIMARY_PRESENTER_COMPANY",
        "SECONDARY_PRESENTER",
        "SECONDARY_PRESENTER_COMPANY",
        "PRESENTER_TYPE_CODE",
        "RATING",
        "RANK"
    )
    AS
SELECT
    y."SESSION_EVENT"                        AS "SESSION_EVENT",
    y."SESSION_CODE"                        AS "SESSION_CODE",
    e."PRIMARY_PRESENTER_FIRSTNAME" || ' ' || e."PRIMARY_PRESENTER_LASTNAME"          AS "PRIMARY_PRESENTER",
    e."PRIMARY_PRESENTER_COMPANY"            AS "PRIMARY_PRESENTER_COMPANY",
    e."SECONDARY_PRESENTER_FIRSTNAME" || ' ' || e."SECONDARY_PRESENTER_LASTNAME"   AS "SECONDARY_PRESENTER",
    e."SECONDARY_PRESENTER_COMPANY"  AS "SECONDARY_PRESENTER_COMPANY",
    e."PRESENTER_TYPE_CODE"                    AS "PRESENTER_TYPE_CODE",
    y."RATING"                             AS "RATING",
    RANK() OVER (ORDER BY y."RATING" DESC) AS "RANK"
FROM
    (   SELECT
            x."SESSION_EVENT",
            x."SESSION_CODE",
            ROUND(AVG(x."SCORE_TOTAL" / x."SCORE_COUNT"), 2) AS "RATING"
        FROM
            (   SELECT
                    "SESSION_EVENT",
                    "SESSION_CODE",
                    COALESCE("OVERALL_SCORE", 0) + COALESCE("SPEAKER_SCORE", 0) + COALESCE("MATERIAL_SCORE", 0) AS "SCORE_TOTAL",
                    CASE
                        WHEN "OVERALL_SCORE" IS NULL
                        THEN 0
                        ELSE 1
                    END +
                    CASE
                        WHEN "SPEAKER_SCORE" IS NULL
                        THEN 0
                        ELSE 1
                    END +
                    CASE
                        WHEN "MATERIAL_SCORE" IS NULL
                        THEN 0
                        ELSE 1
                    END AS "SCORE_COUNT"
                FROM
                    "vote"."SCORE"
                WHERE
                    COALESCE("OVERALL_SCORE", "SPEAKER_SCORE", "MATERIAL_SCORE") IS NOT NULL) x
        GROUP BY
            x."SESSION_EVENT", x."SESSION_CODE"
        HAVING
            COUNT(*) >= 10  ) y
JOIN "vote"."SESSION" e ON y."SESSION_EVENT" = e."SESSION_EVENT" and y."SESSION_CODE" = e."SESSION_CODE"
INNER JOIN "vote"."PRESENTER_TYPE" p ON e."PRESENTER_TYPE_CODE" = p."PRESENTER_TYPE_CODE" ;







CREATE VIEW
    "vote"."TRACKS"
    (
        "SESSION_EVENT",
        "SESSION_CODE",
        "SPEAKER",
        "NB_EVAL",
        "RATING",
        "RANK"
    )
    AS
SELECT
    y."SESSION_EVENT" as SESSION_EVENT,
    y."SESSION_CODE" AS SESSION_CODE,
    e."PRIMARY_PRESENTER_FIRSTNAME" || ' ' || e."PRIMARY_PRESENTER_LASTNAME"
    || COALESCE((', ' || e."SECONDARY_PRESENTER_FIRSTNAME" || ' ' || e."SECONDARY_PRESENTER_LASTNAME") , '') AS "SPEAKER",
    t."NB_EVAL",
    y."RATING"                             AS "RATING",
    RANK() OVER (ORDER BY y."RATING" DESC) AS "RANK"
FROM
    (   SELECT
            x."SESSION_EVENT",
            x."SESSION_CODE",
            ROUND(AVG(x."SCORE_TOTAL" * 1.0 / x."SCORE_COUNT"), 2) AS "RATING"
        FROM
            (   SELECT
                    "SESSION_EVENT",
                    "SESSION_CODE",
                    COALESCE("OVERALL_SCORE", 0) + COALESCE("SPEAKER_SCORE", 0) + COALESCE("MATERIAL_SCORE", 0) AS "SCORE_TOTAL",
                    CASE
                        WHEN "OVERALL_SCORE" IS NULL
                        THEN 0
                        ELSE 1
                    END +
                    CASE
                        WHEN "SPEAKER_SCORE" IS NULL
                        THEN 0
                        ELSE 1
                    END +
                    CASE
                        WHEN "MATERIAL_SCORE" IS NULL
                        THEN 0
                        ELSE 1
                    END AS "SCORE_COUNT"
                FROM
                    "vote"."SCORE"
                WHERE
                    COALESCE("OVERALL_SCORE", "SPEAKER_SCORE", "MATERIAL_SCORE") IS NOT NULL) x
        GROUP BY
            x."SESSION_EVENT", x."SESSION_CODE") y
JOIN "vote"."SESSION" e ON y."SESSION_EVENT" = e."SESSION_EVENT" and y."SESSION_CODE" = e."SESSION_CODE"
LEFT JOIN
    (   SELECT
            e_1."SESSION_EVENT",
            e_1."SESSION_CODE",
            COUNT(*) AS "NB_EVAL"
        FROM
            "vote"."SCORE" e_1
        GROUP BY
            e_1."SESSION_EVENT", e_1."SESSION_CODE") t
ON
    t."SESSION_EVENT"= e."SESSION_EVENT" and t."SESSION_CODE" = e."SESSION_CODE";








CREATE VIEW
    "vote"."MODERATORS"
    (
        "SESSION_EVENT",
        "SESSION_CODE",
        "DATE",
        "SESSION_DATE",
        "SESSION_TIME",
        "SESSION_TITLE",
        "SPEAKER",
        "MODERATOR_NAME",
        "SUBJECT_DESC",
        "SEARCH"
    )
    AS
WITH
    temp1 AS
    (   SELECT
            s."SESSION_EVENT" AS "SESSION_EVENT",
            s."SESSION_CODE"  AS "SESSION_CODE",
            s."SESSION_DATE" as "DATE",
            TO_CHAR(s."SESSION_DATE", 'Dy, FMDDth FMMon') as "SESSION_DATE",
            TO_CHAR(s."SESSION_START", 'HH24:MI') || '-' || TO_CHAR(s."SESSION_END", 'HH24:MI') as "SESSION_TIME",
            s."SESSION_TITLE" AS "SESSION_TITLE",
            s."PRIMARY_PRESENTER_FIRSTNAME" || ' ' || s."PRIMARY_PRESENTER_LASTNAME"
            || COALESCE((', ' || s."SECONDARY_PRESENTER_FIRSTNAME" || ' ' || s."SECONDARY_PRESENTER_LASTNAME") , '') AS "SPEAKER",
            m."MODERATOR_NAME",
            p."SUBJECT_DESC"
        FROM
            "vote"."SESSION" s
            inner join "vote"."SUBJECT" p on p."SUBJECT_ID" = s."SUBJECT_ID"
            left join "vote"."MODERATOR" m on m."SESSION_EVENT"= s."SESSION_EVENT" and m."SESSION_CODE" = s."SESSION_CODE"
    )
    ,
    temp2 AS
    (   SELECT
            temp1."SESSION_EVENT",
            temp1."SESSION_CODE",
            temp1."DATE",
            temp1."SESSION_DATE",
            temp1."SESSION_TIME",
            temp1."SESSION_TITLE",
            temp1."SPEAKER",
            temp1."MODERATOR_NAME",
            temp1."SUBJECT_DESC",
            ((((temp1."SESSION_CODE" || ' ') || temp1."SESSION_TITLE") || ' ') || temp1."SPEAKER")
            || COALESCE(temp1."MODERATOR_NAME", '')
            || ' ' || temp1."SESSION_DATE" || ' ' || temp1."SESSION_TIME" || ' ' || temp1."SUBJECT_DESC" AS "SEARCH"
        FROM
            temp1
    )
SELECT
    temp2."SESSION_EVENT",
    temp2."SESSION_CODE",
    temp2."DATE",
    temp2."SESSION_DATE",
    temp2."SESSION_TIME",
    temp2."SESSION_TITLE",
    temp2."SPEAKER",
    temp2."MODERATOR_NAME",
    temp2."SUBJECT_DESC",
    temp2."SEARCH"
FROM
    temp2;





-------------------------------------------------------------------------------------------------------


CREATE VIEW "vote"."VSESSIONS"
("SESSION_EVENT", "SESSION_CODE" ,"SESSION_TITLE"
,"PRIMARY_PRESENTER", "PRIMARY_PRESENTER_COMPANY"
,"SECONDARY_PRESENTER","SECONDARY_PRESENTER_COMPANY"
,"PRESENTER_TYPE"
,"SCORE_COUNT" ,"SCORE" ,"SCORE_NOTES")
AS
WITH
SCORES ("SESSION_EVENT", "SESSION_CODE", "SCORE_COUNT", "SCORE")
AS ( SELECT "SESSION_EVENT", "SESSION_CODE", COUNT(*),
(sum(COALESCE("OVERALL_SCORE", 0)) + sum(COALESCE("SPEAKER_SCORE", 0)) + sum(COALESCE("MATERIAL_SCORE", 0)))
FROM "vote"."SCORE" GROUP BY "SESSION_EVENT", "SESSION_CODE" ),

SCORE_NOTES ("SESSION_EVENT", "SESSION_CODE", "SCORE_NOTES")
AS ( SELECT "SESSION_EVENT", "SESSION_CODE", string_agg(rtrim("NOTES"),'#')
FROM "vote"."SCORE" WHERE "NOTES" <> '' GROUP BY "SESSION_EVENT", "SESSION_CODE" )

SELECT
S."SESSION_EVENT", S."SESSION_CODE", S."SESSION_TITLE",
S."PRIMARY_PRESENTER_FIRSTNAME" || ' ' || S."PRIMARY_PRESENTER_LASTNAME" as "PRIMARY_PRESENTER", S."PRIMARY_PRESENTER_COMPANY",
S."SECONDARY_PRESENTER_FIRSTNAME" || ' ' || S."SECONDARY_PRESENTER_LASTNAME" as SECONDARY_PRESENTER, S."SECONDARY_PRESENTER_COMPANY",
P."PRESENTER_TYPE_DESC",
X."SCORE_COUNT",
CASE
    WHEN COALESCE(x."SCORE", 0) = 0 THEN NULL
    ELSE
(CAST(COALESCE(X."SCORE",0) AS DECIMAL(8,3))) / (COALESCE(X."SCORE_COUNT",1) * 3)
END
, N."SCORE_NOTES"
FROM
"vote"."SESSION" S
INNER JOIN "vote"."PRESENTER_TYPE" P ON S."PRESENTER_TYPE_CODE" = P."PRESENTER_TYPE_CODE"
LEFT OUTER JOIN SCORES X ON S."SESSION_EVENT" = X."SESSION_EVENT" and S."SESSION_CODE" = X."SESSION_CODE"
LEFT OUTER JOIN SCORE_NOTES N ON S."SESSION_EVENT" = N."SESSION_EVENT" and S."SESSION_CODE" = N."SESSION_CODE";


-----------------------


CREATE VIEW "vote"."VSTATISTICS"
("TOTAL_SESSIONS" ,"COMPLETED_SESSIONS" ,"BEST_SPEAKER", "BEST_USER_SPEAKER")
AS
VALUES (
(SELECT COUNT(*) FROM "vote"."VSESSIONS"),
(SELECT COUNT(*) FROM "vote"."VSESSIONS" WHERE "SCORE_COUNT" > 0) ,
(SELECT RTRIM("PRIMARY_PRESENTER") || ' (' || RTRIM(cast(CAST("SCORE" AS DECIMAL(4,3)) as varchar(5))) || ')' FROM "vote"."VSESSIONS" WHERE "SCORE_COUNT" > 10 ORDER BY "SCORE"
DESC FETCH FIRST 1 ROWS ONLY) ,
(SELECT RTRIM("PRIMARY_PRESENTER") || ' (' || RTRIM(cast(CAST("SCORE" AS DECIMAL(4,3)) as varchar(5))) || ')' FROM "vote"."VSESSIONS"
WHERE "PRESENTER_TYPE" = 'User/Consultant' AND "SCORE_COUNT" > 10 ORDER BY "SCORE"
DESC FETCH FIRST 1 ROWS ONLY)
);

---------------------------------------------



CREATE VIEW "vote"."VMODAVAIL"
("SESSION_EVENT", "SESSION_CODE" ,"SESSION_TITLE"
,"PRIMARY_PRESENTER", "PRIMARY_PRESENTER_COMPANY"
,"SECONDARY_PRESENTER","SECONDARY_PRESENTER_COMPANY"
,"PRESENTER_TYPE" )
AS
SELECT S."SESSION_EVENT", S."SESSION_CODE",
S."SESSION_TITLE",
S."PRIMARY_PRESENTER_FIRSTNAME" || ' ' || S."PRIMARY_PRESENTER_LASTNAME" as "PRIMARY_PRESENTER", S."PRIMARY_PRESENTER_COMPANY",
S."SECONDARY_PRESENTER_FIRSTNAME" || ' ' || S."SECONDARY_PRESENTER_LASTNAME" as "SECONDARY_PRESENTER", S."SECONDARY_PRESENTER_COMPANY",
P."PRESENTER_TYPE_DESC"
FROM
"vote"."SESSION"    S
INNER JOIN "vote"."PRESENTER_TYPE" P ON S."PRESENTER_TYPE_CODE" = P."PRESENTER_TYPE_CODE"
WHERE S."MODERATOR_STATUS_ID" = 0;



----------------------------------

CREATE VIEW "vote"."VMODTAKEN"
("SESSION_EVENT", "SESSION_CODE" ,"SESSION_TITLE"
,"PRIMARY_PRESENTER", "PRIMARY_PRESENTER_COMPANY"
,"SECONDARY_PRESENTER","SECONDARY_PRESENTER_COMPANY"
,"PRESENTER_TYPE" ,
"MODERATOR_NAME", "MODERATOR_EMAIL" )
AS
SELECT S."SESSION_EVENT", S."SESSION_CODE",
S."SESSION_TITLE",
S."PRIMARY_PRESENTER_FIRSTNAME" || ' ' || S."PRIMARY_PRESENTER_LASTNAME" as "PRIMARY_PRESENTER", S."PRIMARY_PRESENTER_COMPANY",
S."SECONDARY_PRESENTER_FIRSTNAME" || ' ' || S."SECONDARY_PRESENTER_LASTNAME" as "SECONDARY_PRESENTER", S."SECONDARY_PRESENTER_COMPANY",
P."PRESENTER_TYPE_DESC",
X."MODERATOR_NAME", X."MODERATOR_EMAIL"
FROM "vote"."SESSION"    S
INNER JOIN "vote"."PRESENTER_TYPE" P ON S."PRESENTER_TYPE_CODE" = P."PRESENTER_TYPE_CODE"

INNER JOIN "vote"."MODERATOR" X ON S."SESSION_EVENT" = X."SESSION_EVENT" and S."SESSION_CODE" = X."SESSION_CODE"
WHERE S."MODERATOR_STATUS_ID" <> 0;

---------------------------------------------


CREATE VIEW "vote"."VMODALL"
("SESSION_EVENT", "SESSION_CODE" ,"SESSION_TITLE"
,"PRIMARY_PRESENTER", "PRIMARY_PRESENTER_COMPANY"
,"SECONDARY_PRESENTER","SECONDARY_PRESENTER_COMPANY"
,"PRESENTER_TYPE" ,
"MODERATOR_NAME", "MODERATOR_EMAIL" )
AS
SELECT S."SESSION_EVENT", S."SESSION_CODE",
S."SESSION_TITLE",
S."PRIMARY_PRESENTER_FIRSTNAME" || ' ' || S."PRIMARY_PRESENTER_LASTNAME" as "PRIMARY_PRESENTER", S."PRIMARY_PRESENTER_COMPANY",
S."SECONDARY_PRESENTER_FIRSTNAME" || ' ' || S."SECONDARY_PRESENTER_LASTNAME" as "SECONDARY_PRESENTER", S."SECONDARY_PRESENTER_COMPANY",
P."PRESENTER_TYPE_DESC",
X."MODERATOR_NAME", X."MODERATOR_EMAIL"
FROM "vote"."SESSION"    S
INNER JOIN "vote"."PRESENTER_TYPE" P ON S."PRESENTER_TYPE_CODE" = P."PRESENTER_TYPE_CODE"

INNER JOIN "vote"."MODERATOR" X ON S."SESSION_EVENT" = X."SESSION_EVENT" and S."SESSION_CODE" = X."SESSION_CODE";


---------------------------------
---------------------------------









INSERT INTO "vote"."SESSION" ("SESSION_EVENT","SESSION_CODE","SESSION_DATE","SESSION_START","SESSION_END","SESSION_NUMBER","SESSION_TITLE","SUBJECT_ID",
"PRIMARY_PRESENTER_FIRSTNAME","PRIMARY_PRESENTER_LASTNAME","PRIMARY_PRESENTER_COMPANY","SECONDARY_PRESENTER_FIRSTNAME","SECONDARY_PRESENTER_LASTNAME",
"SECONDARY_PRESENTER_COMPANY","PRESENTER_TYPE_CODE")


VALUES



('EMEA2025','A1', '10/27/2025', '10:20', '11:20', 'SESS-162', 'Db2 for z/OS: Trends and Directions', '1', 'Haakon', 'Roberts', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','A2', '10/27/2025', '11:30', '12:30', 'SESS-89', 'Db2 13 for z/OS Experience with new features for Availability, Resilience and Performance', '1', 'John', 'Campbell', 'Triton Consulting', NULL, NULL, NULL, '1'),
('EMEA2025','A3', '10/27/2025', '14:00', '15:00', 'SESS-217', 'Db2 13 for z/OS - Five Key Features to Drive Performance and Innovation', '1', 'Preetham', 'Kannan', 'Rocket Software', 'Vishwa', 'Thakur', 'Rocket Software', '5'),
('EMEA2025','A4', '10/27/2025', '15:20', '16:20', 'SESS-127', 'The Latest Db2 13 Online schema evolution and application performance enhancements', '1', 'Frances', 'Villafuerte', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','A5', '10/27/2025', '16:30', '17:30', 'SESS-25', 'Db2 Analytics Accelerator:  product updates, new version V8, and experiences from the customers and health checks', '1', 'Cuneyt', 'Goksu', 'IBM ', 'Björn ', 'Broll', 'IBM', '2'),
('EMEA2025','A6', '10/28/2025', '10:20', '11:20', 'SESS-40', 'Optimizing SQL Pagination in Db2 for z/OS for Performance Gains', '1', 'Emil', 'Kotrc', 'Broadcom', NULL, NULL, NULL, '4'),
('EMEA2025','A7', '10/28/2025', '11:30', '12:30', 'SESS-136', 'Db2 13 latest real customer experiences - new functions, best practices and some more…', '1', 'Ute', 'Kleyensteuber', 'Commerzbank AG', NULL, NULL, NULL, '1'),
('EMEA2025','A8', '10/28/2025', '14:00', '15:00', 'SESS-91', 'Dynamic SQL Monitoring: Best Practices', '1', 'Michal', 'Bialecki', 'Broadcom', NULL, NULL, NULL, '4'),
('EMEA2025','A9', '10/28/2025', '16:30', '17:30', 'SESS-123', 'Db2 System and Application monitoring and alert system approach', '1', 'Hakan', 'Kahraman', 'Garanti BBVA', 'Toine', 'Michielse', 'Broadcom', '1'),
('EMEA2025','A10', '10/29/2025', '10:20', '11:20', 'SESS-73', 'Supercharge Db2 Utilities: Uncover More Features', '1', 'Denis', 'Tronin', 'Broadcom', NULL, NULL, NULL, '4'),
('EMEA2025','A11', '10/29/2025', '11:30', '12:30', 'SESS-3', 'BMC Db2 AMI Utilities To The Rescue - What''s New !!', '1', 'Michael', 'Cotignola', 'BMC Software', NULL, NULL, NULL, '3'),
('EMEA2025','A12', '10/29/2025', '14:00', '15:00', 'SESS-163', 'Db2 for z/OS Utilities – Unveiling recent updates and current developments', '1', 'Haakon', 'Roberts', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','A14', '10/29/2025', '17:40', '18:40', 'SESS-153', 'Tools maintanance our way', '1', 'Martin', 'Ålund', 'Handelsbanken', NULL, NULL, NULL, '1'),
('EMEA2025','A15', '10/30/2025', '09:00', '10:00', 'SESS-184', 'Billions of XMLs! How Do You Manage That?', '1', 'Philip', 'Nelson', 'Lloyds Banking Group / ScotDB Limited', NULL, NULL, NULL, '1'),
('EMEA2025','A16', '10/30/2025', '10:20', '11:20', 'SESS-38', 'All about the Db2 Log: Updates, Commits, and Best Practices for Data Integrity', '1', 'Emil', 'Kotrc', 'Broadcom', NULL, NULL, NULL, '4'),
('EMEA2025','A17', '10/30/2025', '11:30', '12:30', 'SESS-1', 'Claims, Drains and Automobiles', '1', 'Marcus', 'Davage', 'BMC Software Ltd', NULL, NULL, NULL, '3'),



('EMEA2025','B2', '10/27/2025', '11:30', '12:30', 'SESS-30', 'RUNSTATS Master - reloaded', '1', 'Roy', 'Boxwell', 'Software Engineering GmbH', NULL, NULL, NULL, '6'),
('EMEA2025','B3', '10/27/2025', '14:00', '15:00', 'SESS-203', 'Key Performance Updates, zSynergy and Best Practices for Db2 for z/OS', '1', 'Akiko', 'Hoshikawa', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','B4', '10/27/2025', '15:20', '16:20', 'SESS-63', 'Taming Page Splits: Reduced Stress for DBAs in Db2 13', '1', 'Saurabh', 'Pandey', 'BMC Software', NULL, NULL, NULL, '3'),
('EMEA2025','B5', '10/27/2025', '16:30', '17:30', 'SESS-239', 'Build a lightweight monitor to identify SQL workload tuning potential', '1', 'Kai', 'Stroh', 'UBS Hainer GmbH', NULL, NULL, NULL, '1'),
('EMEA2025','B6', '10/28/2025', '10:20', '11:20', 'SESS-82', 'Db2 under siege: real-world exploits and defence strategies', '1', 'David', 'Lea', 'BMC Software Ltd', 'Marcus', 'Davage', 'BMC Software Ltd', '3'),
('EMEA2025','B7', '10/28/2025', '11:30', '12:30', 'SESS-74', 'Mastering Access Path Management in Db2 for z/OS: Simplify, Optimize, Succeed', '1', 'Denis', 'Tronin', 'Broadcom', NULL, NULL, NULL, '4'),
('EMEA2025','B8', '10/28/2025', '14:00', '15:00', 'SESS-12', '"Run-It-Back" - Db2 for z/OS Development all new "2025 SWAT Tales"', '1', 'Anthony', 'Ciabattoni', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','B9', '10/28/2025', '16:30', '17:30', 'SESS-222', 'Protecting your Db2 for z/OS environment from cyber attacks', '1', 'Patric', 'Becker', 'Rocket Software', NULL, NULL, NULL, '5'),
('EMEA2025','B10', '10/29/2025', '10:20', '11:20', 'SESS-267', 'Db2 for z/OS Tablespace Update', '1', 'David', 'Simpson', 'Huntington Bank', NULL, NULL, NULL, '1'),
('EMEA2025','B11', '10/29/2025', '11:30', '12:30', 'SESS-59', 'Personal Experience: 40 Years of Battle Scars from Managing Db2 for z/OS', '1', 'Steen', 'Rasmussen', 'Broadcom', NULL, NULL, NULL, '4'),
('EMEA2025','B12', '10/29/2025', '14:00', '15:00', 'SESS-238', 'in memory table : what did you expect ?', '1', 'Laurent', 'Kuperberg', 'SQLK', NULL, NULL, NULL, '1'),
('EMEA2025','B13', '10/29/2025', '16:30', '17:30', 'SESS-23', 'Db2 Basics: An introduction to External Tables including remote storage 💾', '2', 'Henrik', 'Loeser', 'IBM Germany', NULL, NULL, NULL, '2'),
('EMEA2025','B14', '10/29/2025', '17:40', '18:40', 'SESS-279', 'Fun with SQL (IDUG content Committee)', '4', 'Julia', 'Carter', 'Broadcom', NULL, NULL, NULL, '4'),
('EMEA2025','B15', '10/30/2025', '09:00', '10:00', 'SESS-170', 'Who’s in Your DB2? Auditing z/OS Like a Mainframe Maestro', '1', 'Jørn', 'Thyssen', 'Rocket Software', 'Christoph', 'Theisen', 'Rocket Software', '5'),
('EMEA2025','B16', '10/30/2025', '10:20', '11:20', 'SESS-140', 'ISBANK''S Journey to implement CDC IIDR Remote Capture with a Resilient Architecture', '1', 'ONDER', 'CAGATAY', 'İŞBANK A.Ş', 'GULFEM', 'OGUTGEN', 'IBM', '1'),
('EMEA2025','B17', '10/30/2025', '11:30', '12:30', 'SESS-215', 'Automating Excellence: Real-world z/OSMF Workflows for Efficient Provisioning and Maintenance (a Db2 Use Case)', '1', 'Josiane ', 'Rodrigues da Silva Ramalho', 'Broadcom Software', NULL, NULL, NULL, '4'),



('EMEA2025','C1', '10/27/2025', '10:20', '11:20', 'SESS-84', 'Db2 Latest from the Lab', '2', 'Mike', 'Springgay', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','C2', '10/27/2025', '11:30', '12:30', 'SESS-133', 'Latest from the Lab on Db2 Warehousing + Lakehouse', '2', 'David', 'Kalmuk', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','C3', '10/27/2025', '14:00', '15:00', 'SESS-247', 'The evolution of the AI Query Tuner agent behind DBAssist', '2', 'Calisto', 'Zuzarte', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','C4', '10/27/2025', '15:20', '16:20', 'SESS-278', 'Db2 12.1.3 - Latest News', '2', 'David', 'Kalmuk', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','C5', '10/27/2025', '16:30', '17:30', 'SESS-210', 'Db2 Availability & Recovery: 12.1 Highlights of What''s New', '2', 'Michael', 'Roecken', 'IBM Canada Ltd.', NULL, NULL, NULL, '2'),
('EMEA2025','C6', '10/28/2025', '10:20', '11:20', 'SESS-113', 'SQL in Action - Mastering & Measuring Data Removal', '2', 'Michael', 'Tiefenbacher', 'mip GmbH', NULL, NULL, NULL, '1'),
('EMEA2025','C7', '10/28/2025', '11:30', '12:30', 'SESS-249', 'Tuning Queries for Performance Using Examples', '2', 'Calisto', 'Zuzarte', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','C8', '10/28/2025', '14:00', '15:00', 'SESS-246', 'Modern Observability for Db2: Prometheus, Grafana & OpenTelemetry in Action', '2', 'Markus', 'Fraune', 'ITGAIN Consulting Gesellschaft für IT Beratung mbH', NULL, NULL, NULL, '6'),
('EMEA2025','C9', '10/28/2025', '16:30', '17:30', 'SESS-57', 'Db2 Performance and Tuning', '2', 'Philip', 'Gunning', 'Gunning Technology Solutions, LLC', NULL, NULL, NULL, '1'),
('EMEA2025','C10', '10/29/2025', '10:20', '11:20', 'SESS-146', 'Evolution of Db2 into Cloud environments at Allianz.AT!', '2', 'Heinz', 'Wiesmüller', 'Allianz Technology AT', NULL, NULL, NULL, '1'),
('EMEA2025','C11', '10/29/2025', '11:30', '12:30', 'SESS-5', 'DB2 Always on architecture', '2', 'Dale', 'McInnis', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','C12', '10/29/2025', '14:00', '15:00', 'SESS-110', 'Db2 and S3 Object Storage : Why? What? How?', '2', 'Philip', 'Nelson', 'Lloyds Banking Group / ScotDB Limited', NULL, NULL, NULL, '1'),
('EMEA2025','C13', '10/29/2025', '16:30', '17:30', 'SESS-151', 'Db2 intensive care - The art of solving Db2 problems', '2', 'Thomas', 'Rech', 'IBM Germany Research & Development GmbH ', 'Zahidul', 'Khan', 'IBM Canada', '2'),
('EMEA2025','C15', '10/30/2025', '09:00', '10:00', 'SESS-225', 'A Db2 governance solution with a modern twist', '2', 'Petri', 'Helin', 'Nordea Bank', NULL, NULL, NULL, '1'),
('EMEA2025','C16', '10/30/2025', '10:20', '11:20', 'SESS-255', 'Db2 V12.1.x: New Security Features and Changes', '2', 'Nataliya', 'Prokoshyna', 'IBM Canada', NULL, NULL, NULL, '2'),
('EMEA2025','C17', '10/30/2025', '11:30', '12:30', 'SESS-268', 'This isn''t just another restore tutorial. It''s a live-fire tale of encrypted Db2 databases, AWS mounts, and GSK gremlins — all tamed in OpenShift’s wild, wild west.', '2', 'Bobby', 'Proffitt', 'DBA/I TopGun', NULL, NULL, NULL, '1'),



('EMEA2025','D2', '10/27/2025', '11:30', '12:30', 'SESS-22', 'Turn red into blue', '2', 'Olaf', 'Stephan', 'BaFin', 'Drik', 'Fechner', 'IBM', '1'),
('EMEA2025','D3', '10/27/2025', '14:00', '15:00', 'SESS-69', 'Review key enhancements for Db2U in modernizing Db2 containerization footprint.', '2', 'Vijaya', 'Katikireddy', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','D4', '10/27/2025', '15:20', '16:20', 'SESS-137', 'Becoming an Expert DBA: Best use of Db2 Features, Improvements & Tips', '2', 'Nemi', 'Agrawal', 'Data Storm Inc', NULL, NULL, NULL, '1'),
('EMEA2025','D5', '10/27/2025', '16:30', '17:30', 'SESS-145', 'Range Partitioning - Overview, Use cases, Tips and Tricks', '2', 'Carola', 'Langwald', 'IBM Deutschland R&D GmbH', 'Phil', 'King', 'IBM', '2'),
('EMEA2025','D6', '10/28/2025', '10:20', '11:20', 'SESS-107', 'Db2 Automatic Statistics Deep Dive', '2', 'John', 'Hornibrook', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','D7', '10/28/2025', '11:30', '12:30', 'SESS-189', 'Db2 – the database of choice for High Availability in a Hybrid/Multi-Cloud Environment', '2', 'Damir', 'Wilder', 'Triton Consulting Ltd.', 'Iqbal', 'Goralwalla', 'Triton Consulting Ltd.', '1'),
('EMEA2025','D8', '10/28/2025', '14:00', '15:00', 'SESS-43', 'Exploring GenAI, RAG, and Semantic Search with Db2 12.1’s Vector Store', '2', 'Marcin', 'Marczewski', 'IBM Poland', NULL, NULL, NULL, '2'),
('EMEA2025','D9', '10/28/2025', '16:30', '17:30', 'SESS-206', 'Monitoring the new multi-tier storage architecture when using Native Cloud Object Storage', '2', 'Robert', 'Hooper', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','D10', '10/29/2025', '10:20', '11:20', 'SESS-111', 'Working with EXPLAIN - Alternatives to Command line and Visual Explain', '2', 'Joachim', 'Klassen', 'LIS.TEC GmbH', NULL, NULL, NULL, '1'),
('EMEA2025','D11', '10/29/2025', '11:30', '12:30', 'SESS-266', 'Using GenAI to quickly build Db2 live monitoring', '2', 'Martin', 'Heitkämper', 'Arvato Systems GmbH', NULL, NULL, NULL, '1'),
('EMEA2025','D12', '10/29/2025', '14:00', '15:00', 'SESS-85', 'V12 Db2 SQL Extensions: Tenant, Vectors, Lakehouse and more', '2', 'Mike', 'Springgay', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','D13', '10/29/2025', '16:30', '17:30', 'SESS-77', 'IBM Db2 for AI: Building AI Systems with Db2', '2', 'Shaikh', 'Quader', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','D14', '10/29/2025', '17:40', '18:40', 'SESS-197', 'Db2 for z/OS Security Basics', '1', 'Gayathiri', 'Chandran', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','D15', '10/30/2025', '09:00', '10:00', 'SESS-7', 'Taking Db2 pureScale to the next level, deploying on z/Linux or LinuxONE', '2', 'Dale', 'McInnis', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','D16', '10/30/2025', '10:20', '11:20', 'SESS-251', 'BACKUP/RESTORE performance insights.', '2', 'Aleksandr', 'Veremev', 'VereData', NULL, NULL, NULL, '1'),
('EMEA2025','D17', '10/30/2025', '11:30', '12:30', 'SESS-132', 'Advanced Performance Diagnostics for SQL', '2', 'David', 'Kalmuk', 'IBM', NULL, NULL, NULL, '2'),




('EMEA2025','E2', '10/27/2025', '11:30', '12:30', 'SESS-205', 'Performing Db2 HADR Upgrades Made Even More Easy', '2', 'Michael', 'Roecken', 'IBM Canada Ltd.', NULL, NULL, NULL, '2'),
('EMEA2025','E3', '10/27/2025', '14:00', '15:00', 'SESS-8', 'DB2 Universal Translator between z/OS and LUW', '4', 'Dale', 'McInnis', 'IBM', 'Jerome', 'Gilbert', 'IBM', '2'),
('EMEA2025','E4', '10/27/2025', '15:20', '16:20', 'SESS-21', 'Fear no Threads: Secure and Monitor Db2 Connections with Profile Tables', '1', 'Toine', 'Michielse', 'Broadcom', NULL, NULL, NULL, '4'),
('EMEA2025','E5', '10/27/2025', '16:30', '17:30', 'SESS-105', 'User Experiences with Pacemaker', '2', 'Damir', 'Wilder', 'Triton Consulting Ltd.', NULL, NULL, NULL, '1'),
('EMEA2025','E6', '10/28/2025', '10:20', '11:20', 'SESS-116', 'Automating and operationalizing data-driven AI with Db2 SQL Data Insights - new APIs for full control', '1', 'Steffen', 'Exner', 'Finanz Informatik GmbH & Co. KG', 'Christian', 'Lenke', 'IBM', '1'),
('EMEA2025','E7', '10/28/2025', '11:30', '12:30', 'SESS-60', 'Transforming your Db2 image Copies to Data Pipelines for Generative AI', '1', 'Mikhael', 'Liberman', 'BMC', NULL, NULL, NULL, '3'),
('EMEA2025','E8', '10/28/2025', '14:00', '15:00', 'SESS-95', 'Deep Dive into SQL Data Insights', '1', 'Thomas', 'Baumann', 'Swiss Mobiliar', NULL, NULL, NULL, '1'),
('EMEA2025','E9', '10/28/2025', '16:30', '17:30', 'SESS-204', 'Unlocking the Power of AI with Db2 for z/OS', '1', 'Akiko', 'Hoshikawa', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','E10', '10/29/2025', '10:20', '11:20', 'SESS-121', 'A Deep dive into Db2 Connect Best Practices', '4', 'Shilu', 'Mathai', 'Rocket Software', NULL, NULL, NULL, '5'),
('EMEA2025','E11', '10/29/2025', '11:30', '12:30', 'SESS-241', 'The Db2 for z/OS Agent -  Lets have a Chat with the Catalog!', '5', 'Daniel', 'Martin', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','E12', '10/29/2025', '14:00', '15:00', 'SESS-62', 'Mastering SQL Performance on IBM Z: Analyzing and Optimizing Queries for Maximum Throughput', '1', 'Saurabh', 'Pandey', 'BMC Software', NULL, NULL, NULL, '3'),
('EMEA2025','E13', '10/29/2025', '16:30', '17:30', 'SESS-233', 'Here''s Looking at YOU, Db2!', '2', 'Ken', 'Shaffer', 'Aerodata Inc. ', NULL, NULL, NULL, '1'),
('EMEA2025','E14', '10/29/2025', '17:40', '18:40', 'SESS-130', 'The ins and outs of High Performance DBATs', '1', 'Bart', 'Steegmans', 'IBM', 'Gareth', 'Copplestone-Jones ', 'Triton Consulting', '2'),
('EMEA2025','E15', '10/30/2025', '09:00', '10:00', 'SESS-80', 'Achieving Resilience with DORA and Db2 Tools: Enhancing Operational Continuity and Compliance', '1', 'Jose ', 'Arias', 'Broadcom', 'Julia', 'Carter', 'Broadcom', '4'),
('EMEA2025','E16', '10/30/2025', '10:20', '11:20', 'SESS-211', 'Native cloud object storage in Db2 Warehouse: AWS or Azure ?', '2', 'Robert', 'Hooper', 'IBM', 'Christian', 'Garcia-Arellano', 'IBM', '2'),
('EMEA2025','E17', '10/30/2025', '11:30', '12:30', 'SESS-46', 'Adopting Agile Development Practices with Db2 for z/OS - Customer Perspective', '1', 'Sueli', 'Almeida', 'IBM Silicon Valley Lab', NULL, NULL, NULL, '2'),





('EMEA2025','F2', '10/27/2025', '11:30', '12:30', 'SESS-65', 'Strategies for Making Db2 Data Accessible with APIs', '1', 'Chris', 'Crone', 'Broadcom', NULL, NULL, NULL, '4'),
('EMEA2025','F3', '10/27/2025', '14:00', '15:00', 'SESS-231', 'Db2 12.1:  Ready for Workloads and Deployments of the Future', '2', 'Les', 'King', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','F4', '10/27/2025', '15:20', '16:20', 'SESS-240', 'Db2 z/OS in a Hybrid Cloud - A Survey of Architecture Options across AWS, Azure, Google and IBM Cloud', '1', 'Daniel', 'Martin', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','F5', '10/27/2025', '16:30', '17:30', 'SESS-17', 'SQL Joins - In Depth', '4', 'Tony', 'Andrews', 'P+T Solutions, Inc.', NULL, NULL, NULL, '1'),
('EMEA2025','F6', '10/28/2025', '10:20', '11:20', 'SESS-18', 'A day in the life of an MFA-enabled Db2 for z/OS DBA', '1', 'Jørn', 'Thyssen', 'Rocket Software', NULL, NULL, NULL, '5'),
('EMEA2025','F7', '10/28/2025', '11:30', '12:30', 'SESS-228', 'Coming back to DSNZPARM roots', '1', 'Manuel', 'Gómez Burriel', 'SpDUG', NULL, NULL, NULL, '1'),
('EMEA2025','F8', '10/28/2025', '14:00', '15:00', 'SESS-94', 'Tales of a DBA with UDFs and Store Procedures', '1', 'Soledad', 'Martinez', 'Volkswagen Group Services', NULL, NULL, NULL, '1'),
('EMEA2025','F9', '10/28/2025', '16:30', '17:30', 'SESS-100', 'Modernize Db2 for z/OS Development with VS Code', '3', 'Scott', 'Davidson', 'Broadcom', 'Brian', 'Jagos', 'Broadcom', '4'),
('EMEA2025','F10', '10/29/2025', '10:20', '11:20', 'SESS-26', 'How to access Db2 for z/OS and other Z data in the cloud', '4', 'Cuneyt', 'Goksu', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','F11', '10/29/2025', '11:30', '12:30', 'SESS-108', 'Desperate Measures - How to Relieve the Db2 Optimizer of its Duties', '2', 'John', 'Hornibrook', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','F12', '10/29/2025', '14:00', '15:00', 'SESS-66', 'Enhance Db2 Performance with Mult-Row Processing Techniques', '1', 'Chris', 'Crone', 'Broadcom', NULL, NULL, NULL, '4'),
('EMEA2025','F13', '10/29/2025', '16:30', '17:30', 'SESS-254', 'Unusual indexes and their usage in Db2', '2', 'Andreas', 'Weininger', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','F14', '10/29/2025', '17:40', '18:40', 'SESS-188', 'Create Stored Procedure to ''Reorg Table'' including table function for Select Reorg() and REST-Services', '1', 'Veit', 'Blaeser', 'BarmeniaGothaer', NULL, NULL, NULL, '1'),
('EMEA2025','F15', '10/30/2025', '09:00', '10:00', 'SESS-214', 'Pedal to The Metal - this is not your Daddy''s Accelerator!', '1', 'Adrian', 'Collett', 'Expertise4IT s.r.l.', NULL, NULL, NULL, '1'),
('EMEA2025','F16', '10/30/2025', '10:20', '11:20', 'SESS-182', 'Modernizing Db2 for z/OS System Management with Ansible', '1', 'Manoj Kumar', 'Jadwani', 'BMC Software', 'Hardik', 'Chawda', 'BMC Software', '3'),
('EMEA2025','F17', '10/30/2025', '11:30', '12:30', 'SESS-235', 'REST API: A New Way to Access Db2', '2', 'Andreas', 'Weininger', 'IBM', NULL, NULL, NULL, '2')




--no D6 & F11

remove

('EMEA2025','D6', '10/28/2025', '10:20', '11:20', 'SESS-107', 'Db2 Automatic Statistics Deep Dive', '2', 'John', 'Hornibrook', 'IBM', NULL, NULL, NULL, '2'),
('EMEA2025','F11', '10/29/2025', '11:30', '12:30', 'SESS-108', 'Desperate Measures - How to Relieve the Db2 Optimizer of its Duties', '2', 'John', 'Hornibrook', 'IBM', NULL, NULL, NULL, '2'),







