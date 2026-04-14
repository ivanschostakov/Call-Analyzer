import { defineConfig } from 'orval';

export default defineConfig({
  callAnalyzer: {
    input: {
      target: './openapi.json',
    },
    output: {
      target: './src/api/generated/client.ts',
      schemas: './src/api/generated/model',
      client: 'react-query',
      httpClient: 'fetch',
      mode: 'split',
      clean: true,
      override: {
        fetch: {
          includeHttpResponseReturnType: false,
        },
        mutator: {
          path: './src/api/http.ts',
          name: 'apiFetch',
        },
      },
    },
  },
});
