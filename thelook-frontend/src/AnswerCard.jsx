export default function AnswerCard({ answer }) {
    const text = answer.answer || answer.summary || answer.message;
    return (
        <div className="answer-card">
            <div>{text}</div>
            {answer.key_figures?.length > 0 && (
                <table className="figures"><tbody>
                    {answer.key_figures.map((f, i) => (
                        <tr key={i}><td>{f.label}</td><td>{f.value}</td></tr>
                    ))}
                </tbody></table>
            )}
            {answer.checkpoints?.length > 0 && (
                <table className="figures">
                    <thead><tr><th>Date</th><th>Forecast</th><th>Range</th></tr></thead>
                    <tbody>
                        {answer.checkpoints.map((p, i) => (
                            <tr key={i}>
                                <td>{p.date}</td>
                                <td>{Math.round(p.value).toLocaleString()}</td>
                                <td>{Math.round(p.lower).toLocaleString()} – {Math.round(p.upper).toLocaleString()}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
            {answer.sql && <details className="sql-box"><summary>SQL</summary><pre>{answer.sql}</pre></details>}
            {answer.failure_reason && <div className="failure">{answer.failure_reason}</div>}
        </div>
    );
}