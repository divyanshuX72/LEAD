import { useState } from 'react';
import type { KeyboardEvent } from 'react';
import { X } from 'lucide-react';

interface KeywordInputProps {
  value: string[];
  onChange: (keywords: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function KeywordInput({ value, onChange, placeholder, disabled }: KeywordInputProps) {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addKeyword();
    }
  };

  const addKeyword = () => {
    const trimmed = inputValue.trim().replace(/,$/, '');
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
      setInputValue('');
    }
  };

  const removeKeyword = (index: number) => {
    const newKeywords = [...value];
    newKeywords.splice(index, 1);
    onChange(newKeywords);
  };

  return (
    <div className={`flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-white p-2 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent ${disabled ? 'opacity-50' : ''}`}>
      {value.map((keyword, index) => (
        <span 
          key={index} 
          className="flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-1 text-sm font-medium text-blue-800"
        >
          {keyword}
          <button
            type="button"
            onClick={() => removeKeyword(index)}
            disabled={disabled}
            className="rounded-full p-0.5 hover:bg-blue-200"
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={addKeyword}
        disabled={disabled}
        placeholder={value.length === 0 ? placeholder : ''}
        className="flex-1 min-w-[120px] bg-transparent text-sm focus:outline-none disabled:cursor-not-allowed"
      />
    </div>
  );
}
