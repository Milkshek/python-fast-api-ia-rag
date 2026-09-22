import type { Exchange } from './types'

export function ExchangeCard({ exchange }: { exchange: Exchange }) {
  return (
    <article className="exchange" aria-label={`Échange ${exchange.sequence}`}>
      <div className="question-bubble">
        <span className="eyebrow">VOUS</span>
        <p>{exchange.question}</p>
      </div>
      <div className="answer-bubble">
        <span className="eyebrow">DOCUMENT INTELLIGENCE</span>
        {exchange.abstained && (
          <span className="badge">Information insuffisante</span>
        )}
        <p>{exchange.answer}</p>
        {exchange.sources.length > 0 && (
          <details className="answer-sources">
            <summary>Sources utilisées ({exchange.sources.length})</summary>
            <ul>
              {exchange.sources.map((source) => (
                <li key={source.id}>
                  <strong>Page {source.chunk.page_number}</strong>
                  <span className="source-reference">
                    {' '}
                    · Source {source.id}
                  </span>
                  <blockquote>{source.chunk.text}</blockquote>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </article>
  )
}
