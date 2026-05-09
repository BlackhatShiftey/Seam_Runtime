import { describe, it, expect } from 'vitest';
import {
  fetchHealth,
  fetchStats,
  fetchCompile,
  fetchSearch,
  fetchContext,
  fetchPersist,
  fetchLosslessCompress,
} from './apiClient';

describe('apiClient', () => {
  it('exports fetchHealth and it is a function', () => {
    expect(fetchHealth).toBeDefined();
    expect(typeof fetchHealth).toBe('function');
  });

  it('exports fetchStats and it is a function', () => {
    expect(fetchStats).toBeDefined();
    expect(typeof fetchStats).toBe('function');
  });

  it('exports fetchCompile and it is a function', () => {
    expect(fetchCompile).toBeDefined();
    expect(typeof fetchCompile).toBe('function');
  });

  it('exports fetchSearch and it is a function', () => {
    expect(fetchSearch).toBeDefined();
    expect(typeof fetchSearch).toBe('function');
  });

  it('exports fetchContext and it is a function', () => {
    expect(fetchContext).toBeDefined();
    expect(typeof fetchContext).toBe('function');
  });

  it('exports fetchPersist and it is a function', () => {
    expect(fetchPersist).toBeDefined();
    expect(typeof fetchPersist).toBe('function');
  });

  it('exports fetchLosslessCompress and it is a function', () => {
    expect(fetchLosslessCompress).toBeDefined();
    expect(typeof fetchLosslessCompress).toBe('function');
  });
});
