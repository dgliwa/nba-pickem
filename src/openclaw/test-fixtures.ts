import type { DailyReport } from "./types.js";

export function reportFixture(): DailyReport {
  return {
    report_date: "2026-10-21",
    season: 2027,
    today: {
      date: "2026-10-21",
      picks: [{
        game_id: "one",
        away_team_id: "CHI",
        away_team: "Chicago Bulls",
        home_team_id: "MIL",
        home_team: "Milwaukee Bucks",
        pick: "Milwaukee Bucks",
        confidence: 0.623,
      }],
    },
    previous_day: {
      date: "2026-10-20",
      picks: [{
        game_id: "prior",
        away_team_id: "NYK",
        away_team: "New York Knicks",
        home_team_id: "BOS",
        home_team: "Boston Celtics",
        pick: "Boston Celtics",
        confidence: 0.7,
        status: "correct",
        actual_winner: "Boston Celtics",
        score: "101-110",
      }],
    },
    weekly: { start_date: "2026-10-19", end_date: "2026-10-20", correct: 5, graded: 8, percentage: 62.5 },
    season_performance: { start_date: null, end_date: "2026-10-20", correct: 31, graded: 50, percentage: 62, season: 2027 },
  };
}
