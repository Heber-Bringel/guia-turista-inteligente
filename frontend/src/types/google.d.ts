interface GoogleCredentialResponse {
  credential?: string
}

interface GoogleAccountsId {
  initialize(config: { client_id: string; callback: (response: GoogleCredentialResponse) => void; auto_select?: boolean }): void
  renderButton(element: HTMLElement, options: { theme: 'outline'; size: 'large'; text: 'signin_with'; shape: 'rectangular'; width: number }): void
  cancel(): void
}

interface Window {
  google?: { accounts: { id: GoogleAccountsId } }
}
