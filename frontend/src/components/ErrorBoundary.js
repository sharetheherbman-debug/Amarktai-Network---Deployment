import React from 'react';

/**
 * ErrorBoundary Component
 * Catches JavaScript errors anywhere in the child component tree and displays a fallback UI
 * Prevents white-screen crashes in production
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console for debugging
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
    
    // You can also log the error to an error reporting service
    // logErrorToService(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ 
      hasError: false,
      error: null,
      errorInfo: null
    });
  }

  render() {
    if (this.state.hasError) {
      // Fallback UI
      return (
        <div style={{
          padding: '24px',
          background: 'var(--panel)',
          border: '1px solid var(--error)',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <div style={{fontSize: '2rem', marginBottom: '12px'}}>⚠️</div>
          <h3 style={{color: 'var(--error)', marginBottom: '12px'}}>
            {this.props.title || 'Something went wrong'}
          </h3>
          <p style={{color: 'var(--muted)', marginBottom: '16px', fontSize: '0.9rem'}}>
            {this.props.message || 'This section encountered an error and couldn\'t load.'}
          </p>
          
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details style={{
              marginBottom: '16px',
              padding: '12px',
              background: 'var(--bg)',
              borderRadius: '6px',
              textAlign: 'left',
              fontSize: '0.85rem',
              color: 'var(--muted)'
            }}>
              <summary style={{cursor: 'pointer', fontWeight: 600, marginBottom: '8px'}}>
                Error Details (Development Only)
              </summary>
              <pre style={{whiteSpace: 'pre-wrap', wordBreak: 'break-word'}}>
                {this.state.error.toString()}
                {this.state.errorInfo && this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
          
          <button
            onClick={this.handleRetry}
            style={{
              padding: '10px 20px',
              background: 'var(--accent)',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.9rem'
            }}
          >
            🔄 Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
