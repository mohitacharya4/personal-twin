// The twin's identity and first-run prompts. Edit this one file to re-skin the persona
// for a different person or a company knowledge base.
export const persona = {
  name: 'Mohit',
  fullName: 'Mohit Acharya',
  initials: 'MA',
  role: 'Senior Software Engineer',
  tagline: 'Ask my digital twin — grounded in my real documents, answers with sources.',
  // These match the shipped sample corpus (data/sample_corpus) so the app answers well out
  // of the box. Swap them for questions that fit your own documents once you re-ingest.
  starters: [
    'What do you value in engineering?',
    'What projects have you built?',
    'How do you approach testing and observability?',
    'What is your engineering background?',
  ],
};
