SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE audit_logs;
TRUNCATE TABLE votes;
TRUNCATE TABLE voter_eligibility;
TRUNCATE TABLE candidates;
TRUNCATE TABLE elections;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;

-- Seed Users (Password: password123)
INSERT INTO users (id, name, email, voter_id, password_hash, role, department, year, created_at) VALUES
(1, 'System Administrator', 'admin@college.edu', 'ADMIN001', 'scrypt:32768:8:1$xIAtiO8N0DxbSlhM$df4ee0d29c6a4bbcab892a400da9323e6071e65aff675d11e7e9b1254c487564ed43db2156dc58ccad7477027a48428fc9f916bea5536335ac0cd0399eee7dc7', 'admin', 'Administration', 0, NOW()),
(2, 'Alex Mercer', 'alex.m@college.edu', 'CS202601', 'scrypt:32768:8:1$xIAtiO8N0DxbSlhM$df4ee0d29c6a4bbcab892a400da9323e6071e65aff675d11e7e9b1254c487564ed43db2156dc58ccad7477027a48428fc9f916bea5536335ac0cd0399eee7dc7', 'voter', 'Computer Science', 3, NOW()),
(3, 'Sophia Chen', 'sophia.c@college.edu', 'CS202602', 'scrypt:32768:8:1$xIAtiO8N0DxbSlhM$df4ee0d29c6a4bbcab892a400da9323e6071e65aff675d11e7e9b1254c487564ed43db2156dc58ccad7477027a48428fc9f916bea5536335ac0cd0399eee7dc7', 'voter', 'Computer Science', 3, NOW());

-- Seed Active Election
INSERT INTO elections (id, title, description, start_time, end_time, status, created_at) VALUES
(1, 'Student Council Election 2026', 'Annual election for Student Council Executive Roles.', NOW() - INTERVAL 1 HOUR, NOW() + INTERVAL 24 HOUR, 'active', NOW());

-- Seed Candidates
INSERT INTO candidates (id, election_id, name, position, manifesto, photo) VALUES
(1, 1, 'Liam O\'Connor', 'President', 'Focusing on transparent student funding and campus Wi-Fi.', 'cand_liam.jpg'),
(2, 1, 'Maya Patel', 'President', 'Pledging for enhanced career service workshops and greener campus.', 'cand_maya.jpg');

-- Seed Eligibility
INSERT INTO voter_eligibility (id, election_id, voter_id, has_voted) VALUES
(1, 1, 2, 0),
(2, 1, 3, 0);