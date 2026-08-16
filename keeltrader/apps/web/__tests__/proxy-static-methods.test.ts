/** @jest-environment node */

import { NextRequest } from 'next/server';

import { proxy } from '../proxy';


describe('static asset method guard', () => {
  it('rejects non-read methods with 405 and Allow', () => {
    const response = proxy(new NextRequest('https://keeltrader.joyeeassets.com/_next/static/chunks/app.js', {
      method: 'POST',
    }));

    expect(response.status).toBe(405);
    expect(response.headers.get('allow')).toBe('GET, HEAD');
  });

  it.each(['GET', 'HEAD'])('allows %s for static assets', (method) => {
    const response = proxy(new NextRequest('https://keeltrader.joyeeassets.com/_next/static/chunks/app.js', {
      method,
    }));

    expect(response.status).toBe(200);
    expect(response.headers.get('x-middleware-next')).toBe('1');
  });
});
