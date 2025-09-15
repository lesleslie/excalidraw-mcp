/** @type {import('jest').Config} */
module.exports = {
  preset: 'ts-jest',                                      // Use TypeScript Jest preset
  testEnvironment: 'node',                                // Node environment for server testing
  roots: ['<rootDir>/src', '<rootDir>/test'],
  testMatch: [
    '**/__tests__/**/*.+(ts|tsx|js)',                    // Tests in __tests__ directories
    '**/*.(test|spec).+(ts|tsx|js)'                     // Files ending with .test or .spec
  ],
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest'                        // Transform TypeScript files
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',                                 // Include canvas server source
    '!src/**/*.d.ts',                                    // Exclude TypeScript definition files
    '!src/types.ts',                                     // Types file doesn't need coverage
    '!src/**/*.config.ts',                               // Exclude configuration files
    '!**/node_modules/**',                               // Exclude dependencies
    '!**/dist/**'                                        // Exclude built files
  ],
  coverageDirectory: 'coverage',                          // Output directory for coverage reports
  coverageReporters: ['text', 'lcov', 'html'],          // Multiple coverage report formats
  coverageThreshold: {                                    // Enforce 70% minimum coverage requirement
    global: {
      branches: 70,                                       // 70% branch coverage minimum
      functions: 70,                                      // 70% function coverage minimum
      lines: 70,                                          // 70% line coverage minimum
      statements: 70                                      // 70% statement coverage minimum
    }
  },
  setupFilesAfterEnv: ['<rootDir>/test/setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  testTimeout: 10000,
  verbose: true
};
