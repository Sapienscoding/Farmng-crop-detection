import React from 'react';

interface DropdownSelectProps {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}

const DropdownSelect: React.FC<DropdownSelectProps> = ({ label, options, value, onChange }) => {
  return (
    <div className='dropdown-component'>
      <label htmlFor={label}>{label}</label>
      <select
        id={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  );
};

export default DropdownSelect;