import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import type { Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { PrismLight as SyntaxHighlighter } from 'react-syntax-highlighter'
import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash'
import javascript from 'react-syntax-highlighter/dist/esm/languages/prism/javascript'
import json from 'react-syntax-highlighter/dist/esm/languages/prism/json'
import jsx from 'react-syntax-highlighter/dist/esm/languages/prism/jsx'
import markup from 'react-syntax-highlighter/dist/esm/languages/prism/markup'
import typescript from 'react-syntax-highlighter/dist/esm/languages/prism/typescript'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { ChatMessage } from '../api'
import DeveloperDetails from './DeveloperDetails'

SyntaxHighlighter.registerLanguage('javascript', javascript)
SyntaxHighlighter.registerLanguage('js', javascript)
SyntaxHighlighter.registerLanguage('jsx', jsx)
SyntaxHighlighter.registerLanguage('typescript', typescript)
SyntaxHighlighter.registerLanguage('ts', typescript)
SyntaxHighlighter.registerLanguage('json', json)
SyntaxHighlighter.registerLanguage('bash', bash)
SyntaxHighlighter.registerLanguage('html', markup)

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable (e.g. non-HTTPS) */
    }
  }

  return (
    <div className="code-block">
      <div className="code-header">
        <span>{language || 'code'}</span>
        <button className="copy-button" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>
      </div>
      <SyntaxHighlighter
        language={language || 'javascript'}
        style={oneLight}
        customStyle={{ margin: 0, padding: '14px 16px', background: 'transparent', fontSize: '0.875rem' }}
        codeTagProps={{ style: { fontFamily: 'var(--font-mono)' } }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}

const markdownComponents: Components = {
  // Fenced blocks are rendered by `code` with a language class; keep <pre> as a plain wrapper.
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children }) => {
    const text = String(children ?? '')
    const match = /language-([\w-]+)/.exec(className ?? '')
    const isBlock = Boolean(match) || text.includes('\n')
    if (!isBlock) return <code className="inline-code">{children}</code>
    return <CodeBlock language={match?.[1] ?? ''} code={text.replace(/\n$/, '')} />
  },
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
}

export default function Message({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="message user">
        <div className="user-bubble">{message.content}</div>
      </div>
    )
  }

  return (
    <div className="message assistant">
      <div className="assistant-avatar" aria-hidden="true">{'{}'}</div>
      <div className="assistant-body">
        <div className="markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {message.content}
          </ReactMarkdown>
        </div>
        {message.details && <DeveloperDetails details={message.details} />}
      </div>
    </div>
  )
}
