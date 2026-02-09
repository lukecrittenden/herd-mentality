DROP TABLE IF EXISTS Users;
DROP TABLE IF EXISTS UserStatistics;
DROP TABLE IF EXISTS CustomQuestions;

CREATE TABLE Users (
	Username VARCHAR(16) PRIMARY KEY,
	PasswordHash CHAR(32) NOT NULL,
    PasswordSalt CHAR(16) NOT NULL,
	DateCreated DATE NOT NULL
);
CREATE TABLE UserStatistics (
	Username VARCHAR(16) PRIMARY KEY,
	GamesPlayed INT,
	TotalTokens INT,
	TotalWins INT,
	TotalLosses INT
);
CREATE TABLE CustomQuestions (
	Username VARCHAR(16) PRIMARY KEY,
	QuestionText VARCHAR(255) NOT NULL,
	DateCreated DATE NOT NULL
);