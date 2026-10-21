export interface Pick {
    game_id: string;
    away_team_id: string;
    away_team: string;
    home_team_id: string;
    home_team: string;
    pick: string;
    confidence: number;
    status?: "correct" | "incorrect" | "pending";
    actual_winner?: string | null;
    score?: string | null;
}
export interface Performance {
    start_date: string | null;
    end_date: string;
    correct: number;
    graded: number;
    percentage: number | null;
    season?: number;
}
export interface DailyReport {
    report_date: string;
    season: number;
    today: {
        date: string;
        picks: Pick[];
    };
    previous_day: {
        date: string;
        picks: Pick[];
    };
    weekly: Performance;
    season_performance: Performance;
}
export interface PublicationState {
    reportDate: string;
    picksDeliveredAt?: string;
    summaryDeliveredAt?: string;
    completedAt?: string;
    errors: string[];
}
