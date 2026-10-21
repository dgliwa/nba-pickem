export function formatPicks(report) {
    const lines = [`🏀 **NBA Picks — ${displayDate(report.today.date)}**`];
    if (report.today.picks.length === 0) {
        lines.push("No games are currently available to pick today.");
    }
    else {
        lines.push(...report.today.picks.map(formatPick));
    }
    lines.push("", "_Model picks are informational; confidence is the model's estimated win probability._");
    return bounded(lines.join("\n"));
}
export function formatSummary(report) {
    const lines = [`📊 **NBA Pick'em Results — through ${displayDate(report.previous_day.date)}**`, "", "**Previous day**"];
    if (report.previous_day.picks.length === 0) {
        lines.push("No saved picks.");
    }
    else {
        lines.push(...report.previous_day.picks.map(formatResult));
    }
    lines.push("", `**This week:** ${formatPerformance(report.weekly)}`, `**${report.season} season:** ${formatPerformance(report.season_performance)}`);
    return bounded(lines.join("\n"));
}
function formatPick(pick) {
    return `• ${pick.away_team} @ ${pick.home_team} → **${pick.pick}** (${percentage(pick.confidence)})`;
}
function formatResult(pick) {
    if (pick.status === "pending")
        return `⏳ ${pick.away_team} @ ${pick.home_team} — **${pick.pick}** pending`;
    const icon = pick.status === "correct" ? "✅" : "❌";
    const score = pick.score ? `, ${pick.score}` : "";
    return `${icon} ${pick.away_team} @ ${pick.home_team} — picked **${pick.pick}**; ${pick.actual_winner} won${score}`;
}
function formatPerformance(performance) {
    if (performance.graded === 0)
        return "no graded picks yet";
    return `**${performance.correct}/${performance.graded} (${performance.percentage?.toFixed(1)}%)**`;
}
function percentage(value) {
    return `${(value * 100).toFixed(1)}%`;
}
function displayDate(value) {
    return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })
        .format(new Date(`${value}T12:00:00Z`));
}
function bounded(message) {
    if (message.length > 2_000)
        throw new Error(`Discord message exceeds 2,000 characters (${message.length}).`);
    return message;
}
//# sourceMappingURL=format.js.map