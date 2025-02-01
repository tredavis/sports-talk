import React from 'react';
import './Message.css';

interface MessageProps {
    sender: 'user' | 'assistant';
    content: string;
}

const Message: React.FC<MessageProps> = ({ sender, content }) => {
    return (
        <div className={`message ${sender}`}>
            <div className="message-content">{content}</div>
        </div>
    );
};

export default Message;