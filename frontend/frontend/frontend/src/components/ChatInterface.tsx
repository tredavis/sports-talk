import React, { useState, FormEvent } from 'react';
import axios from 'axios';
import Message from './Message';
import './ChatInterface.css';

interface MessageType {
    id: number;
    sender: 'user' | 'assistant';
    content: string;
}

const ChatInterface: React.FC = () => {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<MessageType[]>([]);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (input.trim() === '') return;

        const userMessage: MessageType = {
            id: messages.length + 1,
            sender: 'user',
            content: input,
        };

        setMessages([...messages, userMessage]);
        setInput('');
        setLoading(true);

        console.log(messages);

        try {
            // for each message in the messages array, concatenate it to the userMessage.content before sending to the backend
            const concatenatedMessages = messages.map(msg => msg.content).join('\n');

            const response = await axios.post('http://localhost:8000/ask', {
                question: concatenatedMessages + '\n' + userMessage.content,
            });

            console.log('===============');
            console.log(concatenatedMessages + '\n' + userMessage.content);
            console.log('===============');

            const assistantMessage: MessageType = {
                id: messages.length + 2,
                sender: 'assistant',
                content: response.data.answer,
            };

            setMessages((prevMessages) => [...prevMessages, assistantMessage]);
        } catch (error) {
            console.error('Error fetching response:', error);
            const errorMessage: MessageType = {
                id: messages.length + 2,
                sender: 'assistant',
                content: 'Sorry, there was an error processing your request.',
            };
            setMessages((prevMessages) => [...prevMessages, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-container">
            <h1>Sports Talk Expert</h1>
            <div className="messages">
                {messages.map((msg) => (
                    <Message key={msg.id} sender={msg.sender} content={msg.content} />
                ))}
                {loading && <Message sender="assistant" content="Typing..." />}
            </div>
            <form onSubmit={handleSubmit} className="input-form">
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask your sports question..."
                    rows={3}
                    required
                />
                <button type="submit" disabled={loading}>
                    Send
                </button>
            </form>
        </div>
    );
};

export default ChatInterface;
