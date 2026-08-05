-- SENTINEL – sample_data.sql
-- Run AFTER schema.sql:
--   psql -U sentinel_user -d sentinel -f sample_data.sql
--
-- Creates three users (admin/analyst/viewer, password Sentinel@2024! for all)
-- and a realistic set of POIs, groups, locations, activities, hotspots,
-- intel reports, and entity extras (tags/notes/fields/coordinates).

-- ─────────────────────────────────────────────
-- Users
-- ─────────────────────────────────────────────
-- Password for all users: Sentinel@2024!
-- bcrypt hash generated with rounds=12
INSERT INTO users (username, password, name, role, unit, active) VALUES
  ('admin',   '$2b$12$RsLU1UNqBKsbXgpretAaN.IYk6mtBp1JGyakAYsp4c6hN7B2E1o2y', 'System Administrator',        'ADMIN',   'HQ — IT & Security',   TRUE),
  ('analyst', '$2b$12$RsLU1UNqBKsbXgpretAaN.IYk6mtBp1JGyakAYsp4c6hN7B2E1o2y', 'Senior Intelligence Analyst', 'ANALYST', 'Analysis Division',    TRUE),
  ('viewer',  '$2b$12$RsLU1UNqBKsbXgpretAaN.IYk6mtBp1JGyakAYsp4c6hN7B2E1o2y', 'Liaison Officer',             'VIEWER',  'External Liaison',     TRUE)
ON CONFLICT (username) DO NOTHING;

-- ─────────────────────────────────────────────
-- Locations
-- ─────────────────────────────────────────────
INSERT INTO locations (id, name, description, address, country, notes) VALUES
  (1, 'Kampala Safe House Alpha',    'Residential property used for clandestine meetings', '14 Kololo Hill Drive, Kampala', 'Uganda', 'Rented under alias. Surveillance camera on north wall.'),
  (2, 'Nairobi Logistics Hub',       'Warehouse used for equipment storage and transfer',  'Industrial Area, Lunga Lunga Rd, Nairobi', 'Kenya', 'Night-shift workers observed loading unmarked crates.'),
  (3, 'Mombasa Port Drop Point',     'Shipping container yard, pier 7',                   'Kilindini Harbour, Mombasa', 'Kenya', 'Container MSCU-4471882 flagged by customs.'),
  (4, 'Dar es Salaam Meeting Venue', 'Hotel conference room used twice in Q3',             'Serena Hotel, Ohio St, Dar es Salaam', 'Tanzania', 'Booked under Haraka Consulting Ltd.'),
  (5, 'Bujumbura Border Crossing',   'Land crossing point, vehicle traffic monitored',     'Kobero Border Post, Burundi', 'Burundi', 'High-frequency crossings noted on Tuesdays.'),
  (6, 'Kigali Comms Node',           'Apartment used as communications relay point',       'KG 11 Ave, Kacyiru, Kigali', 'Rwanda', 'Broadband satellite dish installed on roof.'),
  (7, 'Port Louis Financial Corridor', 'Registered office cluster used for shell transfers', 'Rue du Savoy, Port Louis', 'Mauritius', 'Multiple shell companies share this address.')
ON CONFLICT DO NOTHING;

INSERT INTO location_coords (location_id, lat, lng, label) VALUES
  (1, -0.3136,  32.5811, 'Main entrance'),
  (2, -1.3031,  36.8217, 'Warehouse gate'),
  (3, -4.0435,  39.6682, 'Pier 7'),
  (4, -6.8160,  39.2893, 'Hotel lobby'),
  (5, -3.0012,  30.0731, 'Vehicle checkpoint'),
  (6, -1.9441,  30.0619, 'Apartment block'),
  (7, -20.1609, 57.5012, 'Registered office')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Persons of Interest
-- ─────────────────────────────────────────────
INSERT INTO poi (id, alias, first_name, last_name, dob, nationality, risk_level, status, last_seen, last_location, description, notes, contacts) VALUES
  (1,  'Manny / The Broker', 'Emmanuel', 'Okoro',    '1978-03-14', 'Nigerian',  'CRITICAL', 'ACTIVE', '2024-11-22', 'Nairobi, Kenya',        'Believed to coordinate financial transfers across East Africa on behalf of the Haraka Network. Known to travel on two passports.', 'Priority-1 subject. Coordinate any field action with regional liaison before approach.', ARRAY[2,6,7]),
  (2,  'Um Khalid / F.R.',   'Fatima',   'Al-Rashid', '1985-07-22', 'Sudanese',  'HIGH',     'ACTIVE', '2024-09-02', 'Nairobi, Kenya',        'Logistics coordinator. Fluent in Arabic, Swahili, French. Manages cross-border shipment scheduling for the network.', 'Frequently changes SIM cards; comms window is narrow.', ARRAY[1,6]),
  (3,  'The Russian / V.S.', 'Viktor',   'Sorokin',   '1969-11-05', 'Russian',   'HIGH',     'ACTIVE', '2024-10-03', 'Kigali, Rwanda',        'Former signals intelligence officer. Suspected of providing technical support for encrypted comms infrastructure.', 'Former FSB Directorate S (unconfirmed). Treat technical claims with caution pending verification.', ARRAY[9]),
  (4,  'David Chen / Mr. Wei','Chen',     'Wei',       '1982-04-30', 'Chinese',   'MEDIUM',   'ACTIVE', '2024-08-14', 'Mombasa, Kenya',        'Operates a legitimate import/export business as cover. Frequent traveller to Mombasa.', 'Business appears to have genuine trade activity alongside suspected cover use.', ARRAY[1]),
  (5,  'Amina W.',            'Amina',    'Warsame',   '1991-09-17', 'Somali',    'MEDIUM',   'ACTIVE', '2024-11-08', 'Kampala, Uganda',       'Courier. Multiple border crossings documented. Associates with the Okoro network.', 'Travels light, cash-only purchases, avoids digital payment trails.', ARRAY[8]),
  (6,  'JM / The Fixer',      'James',    'Mwangi',    '1975-06-02', 'Kenyan',    'MEDIUM',   'ACTIVE', '2024-11-22', 'Nairobi, Kenya',        'Former police officer. Provides local facilitation and access to a bribery network.', 'Retains contacts inside Nairobi traffic police and customs.', ARRAY[1,2,10]),
  (7,  'Lu / L.F.',           'Luciana',  'Ferreira',  '1988-02-11', 'Brazilian', 'HIGH',     'ACTIVE', '2024-10-11', 'Port Louis, Mauritius', 'Financial analyst. Suspected of routing money-laundering transfers through shell companies.', 'Signatory on at least two Mauritius-registered accounts under review.', ARRAY[1]),
  (8,  'Abu Tariq',           'Ibrahim',  'Hassan',    '1972-12-28', 'Ethiopian', 'CRITICAL', 'ACTIVE', '2024-09-24', 'Kobero, Burundi',       'Believed to lead ground operations for the Kobero Crossing Cell. Low digital footprint; travels by road only.', 'No known phone number. All confirmed sightings are physical/HUMINT.', ARRAY[5]),
  (9,  'Tasha / N.V.',        'Natasha',  'Volkov',    '1993-08-19', 'Ukrainian', 'MEDIUM',   'ACTIVE', '2024-11-15', 'Kigali, Rwanda',        'IT specialist. Sets up encrypted communications infrastructure for the network.', 'Listed as technical director of Techlink Solutions (front company).', ARRAY[3]),
  (10, 'Dan / The Accountant', 'Daniel',  'Otieno',    '1980-05-07', 'Kenyan',    'LOW',      'UNKNOWN', '2024-05-01', 'Nairobi, Kenya',       'Accountant linked to Haraka Consulting Ltd. Possible unwitting associate.', 'No direct evidence of knowing involvement; monitor only.', ARRAY[6])
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Groups of Interest
-- ─────────────────────────────────────────────
INSERT INTO groups_of_interest (id, name, type, threat_level, status, founded, base, leader_id, description, objectives, notes) VALUES
  (1, 'Haraka Network',       'Criminal Organization', 'CRITICAL', 'ACTIVE', '2019', 'Nairobi, Kenya',        1, 'Cross-border smuggling and financial crime network operating across East Africa.', 'Sustain smuggling corridors and launder proceeds through regional shell entities.', 'Estimated 15-30 members. Cell structure; Haraka Consulting Ltd used as a front for bookings.'),
  (2, 'Sauti ya Ukweli',      'Front Organization',     'MEDIUM',   'ACTIVE', '2020', 'Nairobi, Kenya',        6, 'Registered NGO used as a front for fundraising and recruitment.',              'Launder donations and provide plausible cover for network members.', 'Accounts show irregular cash deposits inconsistent with declared NGO activity.'),
  (3, 'Eastern Bridge LLC',   'Shell Company',          'MEDIUM',   'ACTIVE', '2018', 'Port Louis, Mauritius', 7, 'Shell company used for trade-based money laundering.',                        'Move and obscure the origin of network proceeds via layered transfers.', 'Registered in Mauritius. Dormant periods followed by large transfers.'),
  (4, 'Kobero Crossing Cell', 'Criminal Cell',          'HIGH',     'ACTIVE', '2021', 'Kobero, Burundi',       8, 'Operational cell focused on the Burundi–Tanzania border corridor.',           'Facilitate cross-border movement of people and goods for the wider network.', 'Sub-unit of Haraka Network. Ibrahim Hassan believed to command.'),
  (5, 'Techlink Solutions',   'Front Organization',     'MEDIUM',   'ACTIVE', '2022', 'Kigali, Rwanda',        9, 'IT front company used to procure encrypted communications equipment.',        'Supply and maintain secure comms infrastructure for network leadership.', 'Registered in Kigali. Natasha Volkov listed as technical director.')
ON CONFLICT DO NOTHING;

-- Group memberships
INSERT INTO group_members (group_id, poi_id, role) VALUES
  (1, 1, 'Senior Coordinator'),
  (1, 2, 'Logistics'),
  (1, 3, 'Technical Adviser'),
  (1, 4, 'External Contact'),
  (1, 5, 'Courier'),
  (1, 6, 'Local Facilitator'),
  (1, 7, 'Financial'),
  (1, 8, 'Operations Lead'),
  (4, 8, 'Cell Commander'),
  (4, 5, 'Courier'),
  (2, 6, 'Board Member'),
  (2, 10,'Accountant'),
  (3, 7, 'Director'),
  (3, 1, 'Beneficial Owner'),
  (5, 9, 'Technical Director'),
  (5, 3, 'Consultant')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Activities
-- ─────────────────────────────────────────────
INSERT INTO activities (id, poi_id, group_id, type, occurred_on, location, lat, lng, description, severity, reported_by) VALUES
  (1,  1, 1, 'MOVEMENT',      '2024-08-14', 'Mombasa, Kenya',                   -4.0435,  39.6682, 'Container MSCU-4471882 received at pier 7. Okoro and Chen Wei observed at location. CCTV footage obtained; 4 unidentified individuals present.', 'HIGH',     'Field Team Mombasa'),
  (2,  2, 1, 'MEETING',       '2024-09-02', 'Nairobi, Kenya',                   -1.3031,  36.8217, 'Al-Rashid and Mwangi met at logistics hub for approx. 90 minutes. Vehicle plates recorded: KCA 441Z, KBZ 109X.', 'MEDIUM',   'Surveillance Unit'),
  (3,  1, 1, 'MEETING',       '2024-09-18', 'Dar es Salaam, Tanzania',          -6.8160,  39.2893, 'Okoro, Al-Rashid, and Ferreira attended a hotel meeting. Haraka Consulting booking confirmed; room 214 booked 3 nights; unknown 4th attendee.', 'HIGH',     'Liaison Officer'),
  (4,  8, 4, 'MOVEMENT',      '2024-09-24', 'Kobero, Burundi',                  -3.0012,  30.0731, 'Hassan and Warsame crossed the Kobero border with an unmarked vehicle. Vehicle searched, nothing found. Vehicle reg. TZ-44821.', 'MEDIUM',   'Border Patrol'),
  (5,  9, 5, 'COMMUNICATION', '2024-10-03', 'Kigali, Rwanda',                   -1.9441,  30.0619, 'Volkov and Sorokin observed entering the apartment; satellite dish installed same day. Dish pointed toward Indian Ocean arc — possible VSAT.', 'MEDIUM',   'Technical Surveillance'),
  (6,  7, 3, 'FINANCIAL',     '2024-10-11', 'Port Louis, Mauritius',           -20.1609,  57.5012, 'USD 340,000 transferred from Eastern Bridge LLC to three shell accounts. Ferreira linked. Transaction chain traced through Mauritius, UAE, Cyprus.', 'CRITICAL', 'Financial Intelligence Unit'),
  (7,  1, 1, 'SURVEILLANCE',  '2024-11-01', 'Kampala, Uganda',                  -0.3136,  32.5811, 'Multiple vehicles observed at the safe house over a 3-day period. Okoro confirmed present on day 2. Plates cross-referenced with Nairobi sightings.', 'HIGH',     'Surveillance Team Alpha'),
  (8,  5, NULL, 'MOVEMENT',   '2024-11-08', 'Kampala, Uganda',                  -0.3136,  32.5811, 'Warsame departed Kampala by bus, arrived Nairobi 36 hours later carrying a sealed document bag. Bus ticket purchased with cash; bag not inspected.', 'LOW',      'Source Handler'),
  (9,  9, 5, 'FINANCIAL',     '2024-11-15', 'Kigali, Rwanda',                   -1.9441,  30.0619, 'Techlink Solutions purchased 12 encrypted radio units and satellite modems, shipped to Kigali. Invoice value USD 87,000; export licence query raised.', 'MEDIUM',   'Customs Liaison'),
  (10, 1, 1, 'MEETING',       '2024-11-22', 'Nairobi, Kenya',                   -1.3031,  36.8217, 'Okoro, Mwangi, and Al-Rashid met briefly at Wilson Airport departure lounge for 20 minutes. Okoro departed on flight KQ-114.', 'LOW',      'Airport Surveillance')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Hotspots
-- ─────────────────────────────────────────────
INSERT INTO hotspots (id, name, type, risk, lat, lng, note) VALUES
  (1, 'Kampala Safe House Alpha',      'MEETING_POINT', 'HIGH',     -0.3136,  32.5811, 'Recurring meeting location for Haraka Network leadership.'),
  (2, 'Nairobi Logistics Hub',         'LOGISTICS',     'HIGH',     -1.3031,  36.8217, 'Primary warehouse and transfer point for the network.'),
  (3, 'Mombasa Port Drop Point',       'LOGISTICS',     'CRITICAL', -4.0435,  39.6682, 'Container handoff point; flagged by customs on multiple occasions.'),
  (4, 'Kobero Border Crossing',        'SURVEILLANCE',  'MEDIUM',   -3.0012,  30.0731, 'High-frequency vehicle crossings noted on Tuesdays.'),
  (5, 'Kigali Comms Node',             'COMMAND',       'MEDIUM',   -1.9441,  30.0619, 'Encrypted communications relay apartment.'),
  (6, 'Port Louis Financial Corridor', 'FINANCIAL',     'HIGH',    -20.1609,  57.5012, 'Shell-company transfer routing point.')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Intel reports
-- ─────────────────────────────────────────────
INSERT INTO intel_reports (id, title, occurred_on, body, poi_refs, group_refs, locations, victims, analysis_result) VALUES
  (1, 'Haraka Network — Q3 Financial Assessment', '2024-10-15',
      'Analysis of transaction records from Eastern Bridge LLC indicates a sustained pattern of trade-based money laundering routed through Mauritius, UAE, and Cyprus. Luciana Ferreira appears as signatory on the receiving accounts. The pattern is consistent with proceeds generated by the Mombasa container operation on 2024-08-14.',
      '[1,7]', '[1,3]', '["Mombasa, Kenya","Port Louis, Mauritius"]', '[]',
      'HIGH confidence of ongoing trade-based money laundering linked to the Haraka Network''s logistics operations.'),
  (2, 'Kobero Corridor Border Activity Summary', '2024-09-30',
      'Repeated crossings at the Kobero border post correlate with courier movements attributed to Amina Warsame under the direction of Ibrahim Hassan. No contraband has been recovered during searches to date, suggesting either advance warning of checks or a currently-empty run.',
      '[8,5]', '[4]', '["Kobero, Burundi"]', '[]',
      'MEDIUM confidence the corridor is being used for reconnaissance ahead of a larger movement.')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Tags
-- ─────────────────────────────────────────────
INSERT INTO tags (entity_type, entity_id, tag, color) VALUES
  ('person', 1, 'financial',   '#e8c44a'), ('person', 1, 'travel-risk', '#e88a4a'), ('person', 1, 'priority-1', '#e84a4a'),
  ('person', 2, 'logistics',   '#4a8fe8'), ('person', 2, 'multilingual', '#4ae87a'),
  ('person', 3, 'technical',   '#4a8fe8'), ('person', 3, 'sigint',       '#e8c44a'),
  ('person', 4, 'trade-cover', '#4ae87a'), ('person', 4, 'travel-risk',  '#e88a4a'),
  ('person', 5, 'courier',     '#4a8fe8'), ('person', 5, 'border-crossing', '#e8c44a'),
  ('person', 6, 'facilitator', '#4a8fe8'), ('person', 6, 'corruption',      '#e84a4a'),
  ('person', 7, 'financial',   '#e8c44a'), ('person', 7, 'shell-companies', '#e88a4a'),
  ('person', 8, 'operations',  '#e84a4a'), ('person', 8, 'low-profile', '#4a8fe8'), ('person', 8, 'priority-1', '#e84a4a'),
  ('person', 9, 'technical',   '#4a8fe8'), ('person', 9, 'communications', '#4ae87a'),
  ('person',10, 'financial',   '#e8c44a'), ('person',10, 'possible-unwitting', '#4ae87a'),
  ('group', 1, 'priority-1',   '#e84a4a'), ('group', 1, 'cross-border', '#4a8fe8'),
  ('group', 2, 'front-org',    '#4ae87a'), ('group', 2, 'kenya',        '#4a8fe8'),
  ('group', 3, 'financial',    '#e8c44a'), ('group', 3, 'mauritius',   '#4a8fe8'),
  ('group', 4, 'operations',   '#e84a4a'), ('group', 4, 'burundi',     '#4a8fe8'),
  ('group', 5, 'technical',    '#4a8fe8'), ('group', 5, 'comms',       '#4ae87a'),
  ('activity', 1, 'maritime',  '#4a8fe8'), ('activity', 1, 'container', '#e8c44a'),
  ('activity', 5, 'vsat',      '#4a8fe8'), ('activity', 5, 'comms',     '#4ae87a'),
  ('activity', 6, 'financial', '#e8c44a'), ('activity', 6, 'money-laundering', '#e84a4a')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Notes (structured, distinct from the free-text `notes` column)
-- ─────────────────────────────────────────────
INSERT INTO notes (entity_type, entity_id, title, body, note_type, is_pinned) VALUES
  ('person', 1, 'Dual-passport confirmed',   'Second passport (suspected false) confirmed via border-control cross-reference. See custom field for numbers.', 'ASSESSMENT', TRUE),
  ('person', 1, 'Source report — Nov 2024',  'Human source indicates Okoro is planning a further transfer of funds before year end.', 'FIELD_REPORT', FALSE),
  ('group',  1, 'Structure assessment',      'Cell structure appears deliberately compartmentalised; no single member has visibility of the full network.', 'ASSESSMENT', TRUE),
  ('activity', 6, 'Financial follow-up',     'Referred to Financial Intelligence Unit for formal SAR filing.', 'WARNING', FALSE)
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Custom fields
-- ─────────────────────────────────────────────
INSERT INTO custom_fields (entity_type, entity_id, field_key, field_value, field_type) VALUES
  ('person', 1, 'passport_numbers', 'A04412871 (NG), B12938471 (NG - suspected false)', 'TEXT'),
  ('person', 1, 'known_phone',      '+234-803-XXX-XXXX (last active Oct 2024)',        'TEXT'),
  ('person', 2, 'known_email',      'f.rashid.logistics@protonmail.com',                'TEXT'),
  ('person', 3, 'former_employer',  'FSB Directorate S (unconfirmed)',                  'TEXT'),
  ('person', 4, 'company',          'Wei Import Export Ltd, Mombasa',                   'TEXT'),
  ('person', 5, 'travel_docs',      'Somali passport SO-4421983',                       'TEXT'),
  ('person', 7, 'linked_companies', 'Eastern Bridge LLC, Solaris Invest SRL (Cyprus)',  'TEXT'),
  ('person', 8, 'vehicle',          'Toyota Land Cruiser, white, TZ-44821',             'TEXT'),
  ('person', 9, 'skills',           'VSAT, encrypted VoIP, SDR, Tor network administration', 'TEXT'),
  ('group',  1, 'estimated_size',   '15-30 members',                                    'TEXT'),
  ('group',  1, 'estimated_revenue','USD 2-5M annually',                                'TEXT'),
  ('group',  3, 'registered_in',    'Mauritius',                                        'TEXT'),
  ('group',  3, 'account_numbers',  'HSBC Mauritius XXXXXX4421, UAE XXXXXX9981',        'TEXT')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Known locations (per-entity coordinates, distinct from the `locations` table)
-- ─────────────────────────────────────────────
INSERT INTO entity_coordinates (entity_type, entity_id, lat, lng, label, note, observed_on) VALUES
  ('person', 1, -1.3031, 36.8217, 'Suspected residence',   'Long-term surveillance target, unconfirmed address.', '2024-06-01'),
  ('person', 8, -3.0012, 30.0731, 'Border-area base',      'Believed to operate from a compound near the crossing.', '2024-07-15'),
  ('group',  1, -0.3136, 32.5811, 'Kampala safe house',    'Recurring leadership meeting location.', '2024-11-01'),
  ('activity', 1, -4.0435, 39.6682, 'Pier 7 handoff point', 'Exact CCTV-confirmed position.', '2024-08-14')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Timeline events
-- ─────────────────────────────────────────────
INSERT INTO timeline_events (entity_type, entity_id, event_date, title, detail) VALUES
  ('person', 1, '2023-01-15', 'First identified',          'Named in financial intelligence report FIR-2023-0041.'),
  ('person', 1, '2023-09-20', 'Travel to Dubai',            'Entry/exit records obtained from partner agency.'),
  ('person', 1, '2024-04-11', 'Phone intercept',            'Partial intercept referencing "the shipment" and Mombasa.'),
  ('person', 1, '2024-08-14', 'Mombasa sighting',           'CCTV confirmed at Kilindini Harbour pier 7.'),
  ('person', 1, '2024-11-22', 'Nairobi airport sighting',   'Departed KQ-114. Destination: Dubai.'),
  ('person', 8, '2022-06-01', 'First identified',           'Named by human source as Haraka operations lead.'),
  ('person', 8, '2024-09-24', 'Kobero border crossing',     'Crossed with Warsame. Vehicle searched — nothing found.'),
  ('group',  1, '2019-03-01', 'Network established',        'Estimated formation date based on financial record analysis.'),
  ('group',  1, '2024-01-01', 'Increased activity noted',   'Significant uptick in border crossings and financial transfers in Q1 2024.')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- Audit log (seed history so Admin → Access/Activity logs aren't empty)
-- ─────────────────────────────────────────────
INSERT INTO audit_log (ts, user_id, username, action, resource, resource_id, detail, ip) VALUES
  (NOW() - INTERVAL '6 days',  1, 'admin',   'LOGIN',          NULL,      NULL, 'Successful login',            '192.168.1.10'),
  (NOW() - INTERVAL '6 days',  2, 'analyst', 'LOGIN',          NULL,      NULL, 'Successful login',            '192.168.1.14'),
  (NOW() - INTERVAL '5 days',  2, 'analyst', 'CREATE_PERSON',  'person',  '9',  'Created POI record: Natasha Volkov', '192.168.1.14'),
  (NOW() - INTERVAL '5 days',  2, 'analyst', 'CREATE_ACTIVITY','activity','5',  'Logged activity: Kigali Comms Setup', '192.168.1.14'),
  (NOW() - INTERVAL '4 days',  3, 'viewer',  'LOGIN',          NULL,      NULL, 'Successful login',            '192.168.1.22'),
  (NOW() - INTERVAL '4 days',  NULL, 'unknown', 'LOGIN_FAIL',  NULL,      NULL, 'Invalid credentials for username "administrator"', '203.0.113.44'),
  (NOW() - INTERVAL '3 days',  1, 'admin',   'CREATE_USER',    'user',    '3',  'Created user account: viewer', '192.168.1.10'),
  (NOW() - INTERVAL '2 days',  2, 'analyst', 'UPDATE_GROUP',   'group',   '1',  'Updated group record: Haraka Network', '192.168.1.14'),
  (NOW() - INTERVAL '1 days',  1, 'admin',   'BACKUP',         NULL,      NULL, 'Manual database backup created', '192.168.1.10'),
  (NOW() - INTERVAL '4 hours', 2, 'analyst', 'LOGIN',          NULL,      NULL, 'Successful login',            '192.168.1.14')
ON CONFLICT DO NOTHING;

-- Reset sequences so future inserts get correct IDs
SELECT setval('poi_id_seq',                  (SELECT MAX(id) FROM poi));
SELECT setval('groups_of_interest_id_seq',   (SELECT MAX(id) FROM groups_of_interest));
SELECT setval('locations_id_seq',            (SELECT MAX(id) FROM locations));
SELECT setval('activities_id_seq',           (SELECT MAX(id) FROM activities));
SELECT setval('hotspots_id_seq',             (SELECT MAX(id) FROM hotspots));
SELECT setval('intel_reports_id_seq',        (SELECT MAX(id) FROM intel_reports));
SELECT setval('users_id_seq',                (SELECT MAX(id) FROM users));
