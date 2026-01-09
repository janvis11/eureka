import { DependencyList, useCallback, useEffect, useState } from 'react';
import { ApiState } from '../types/api';

export const useAsyncData = <T,>(loader: () => Promise<T>, deps: DependencyList = []): ApiState<T> => {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await loader();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, deps);

  useEffect(() => {
    void run();
  }, [run]);

  return { data, isLoading, error, refresh: run };
};

