using System;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Anthropic.SDK;
using Anthropic.SDK.Constants;
using Anthropic.SDK.Messaging;
using HtmlAgilityPack;
using NAudio.Wave;
using Newtonsoft.Json.Linq;
using OpenAI_API;
using OpenAI_API.Audio;
using OpenAI_API.Chat;
using OpenAI_API.Models;
using static OpenAI_API.Audio.TextToSpeechRequest;

namespace ReadItToMeDotNet;
class Program
{
    // ANSI escape codes for some colors
    private const string RED = "\x1b[31m";
    private const string GREEN = "\x1b[32m";
    private const string YELLOW = "\x1b[33m";
    private const string BLUE = "\x1b[34m";
    private const string MAGENTA = "\x1b[35m";
    private const string CYAN = "\x1b[36m";
    private const string WHITE = "\x1b[37m";
    private const string RESET = "\x1b[0m";  // Resets the color to default

    private static string CLAUDE_KEY;
    private static string API_KEY;
    private static string OUTPUT_DIR;
    private static string SELECTED_MODEL;
    private static string SELECTED_MODEL_TYPE;
    private static string OLLAMA_HOST;
    private static string AUDIO_VOICE;
    private static int MAX_TOKENS;

    static async Task Main(string[] args)
    {
        var config = JObject.Parse(File.ReadAllText("config.json"));
        CLAUDE_KEY = config["CLAUDE_KEY"].ToString();
        API_KEY = config["OPENAI_KEY"].ToString();
        OUTPUT_DIR = config["OUTPUT_DIR"].ToString();
        SELECTED_MODEL = config["SELECTED_MODEL"].ToString();
        SELECTED_MODEL_TYPE = config["SELECTED_MODEL_TYPE"].ToString();
        OLLAMA_HOST = config["OLLAMA_HOST"].ToString();
        AUDIO_VOICE = config["AUDIO_VOICE"].ToString();
        MAX_TOKENS = Int32.Parse(config["MAX_RESPONSE_TOKENS"].ToString());

        string url = null;
        bool downloadOnly = false;
        bool silent = false;
        string fixedFilename = null;

        // Parse command line arguments
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--url")
                url = args[++i];
            else if (args[i] == "--download-only")
                downloadOnly = true;
            else if (args[i] == "--silent")
                silent = true;
            else if (args[i] == "--fixed-filename")
                fixedFilename = args[++i];
        }

        Console.WriteLine("READIT To ME 1.0.");
        Console.WriteLine($"Env: SELECTED_MODEL:{SELECTED_MODEL}, AUDIO_VOICE:{AUDIO_VOICE}, MAX_TOKENS:{MAX_TOKENS}");

        if (!silent)
            PlayMp3("gettingcontent.mp3");

        if (url == null)
            url = "https://news.ycombinator.com/item?id=39865810";  // large discussion used for testing

        var contents = await GetWebPageContentsAsync(url);
        Console.WriteLine($"Word Count from page: {WordCount(contents)}");
        Console.WriteLine($"Tokens Estimate: {EstimateTokens(contents)}");

        var speechFilename = fixedFilename ?? GenerateFilenameFromUrl(url);
        var speechFilePath = Path.Combine(OUTPUT_DIR, speechFilename);
        Console.WriteLine($"Filepath path: {speechFilePath}");

        if (!silent)
            PlayMp3("summary.mp3");

        Console.WriteLine($"Summarizing: {url}");

        var resp = await TalkToAIAsync(contents, SELECTED_MODEL, GREEN, SELECTED_MODEL_TYPE, maxTokens: MAX_TOKENS);

        Console.WriteLine($"SUMMARY: {resp}");

        if (!silent)
            PlayMp3("genaudio.mp3");

        await GenerateAudioAsync(resp, AUDIO_VOICE, speechFilePath);
        Console.WriteLine("Audio generated! Now Playing.");

        if (!downloadOnly)
        {
            Console.WriteLine("Now Playing.");
            PlayMp3(speechFilePath);
        }

        Console.WriteLine("Done!");
    }

    private static void PrintColored(string text, string color)
    {
        Console.Write($"{color}{text}{RESET}");
    }

    private static int EstimateTokens(string text)
    {
        return text.Length / 4;
    }

    private static async Task<string> TalkToAIAsync(string content, string model, string color, string apiType, double temperature = 1, int maxTokens = 720, double topP = 1, double frequencyPenalty = 0, double presencePenalty = 0, string systemPrompt = null)
    {
        string baseSysPrompt = "You are a helpful AI assistant named ROBOT. Provide concise answers to simple questions and thorough responses to complex, open-ended queries.";

        if (systemPrompt == null && apiType == "claude")
            systemPrompt = baseSysPrompt.Replace("ROBOT", "Claude");
        else if (systemPrompt == null && apiType == "openai")
            systemPrompt = baseSysPrompt.Replace("ROBOT", "ChatGPT");

        Console.WriteLine($"Using System Prompt: {systemPrompt}");

        if (apiType == "ollama")
        {
            Console.WriteLine($"Using OLLAMA model: {model} for AI");
            var prompt = $"Please synthesize and provide a detailed overview of the following textual content.\nContent:\n{content}";
            var baseUrl = $"{OLLAMA_HOST}/v1/";
            var apiKey = "ollama";

            var auth = new OpenAI_API.APIAuthentication(apiKey);            
            var client = new OpenAI_API.OpenAIAPI(auth);
            
            var responseParams = new OpenAI_API.Chat.ChatRequest
            {
                Model = model,
                Messages = new[] { new OpenAI_API.Chat.ChatMessage { Role = ChatMessageRole.User, TextContent = prompt } }
            };
            
            var response = await client.Chat.CreateChatCompletionAsync(responseParams);
            var messageContent = response.Choices[0].Message.Content;
            PrintColored($"{model}:", color);
            PrintColored(messageContent, color);
            return messageContent;
        }
        else if (apiType == "claude")
        {
            Console.WriteLine($"Using Claude model: {model} for AI");
            var prompt = $"Please synthesize and provide a detailed overview of the following webpage content.\nWebpage Content:\n{content}";
            var apiKey = CLAUDE_KEY;
            var client = new AnthropicClient(apiKey);

            var messages = new List<Message>();
            messages.Add(new Message()
            {
                Role = RoleType.User,
                Content =prompt
            });
            var responseParams = new MessageParameters
            {
                Messages = messages,
                Model = AnthropicModels.Claude3Opus,
                MaxTokens = maxTokens,
                Temperature = (decimal)temperature,
                SystemMessage = systemPrompt,
                Stream = false,
            };
            var response = await client.Messages.GetClaudeMessageAsync(responseParams);

            var messageContent = response.Content[0].Text;
            PrintColored($"{model}:", color);
            PrintColored( messageContent , color);
            return messageContent;
        }
        else  // Default to GPT
        {
            Console.WriteLine($"Using OpenAI model: {model} for AI");
            var prompt = $"Please synthesize and provide a detailed overview of the following textual content.\nContent:\n{content}";
            var apiKey = API_KEY;
            var auth = new OpenAI_API.APIAuthentication(apiKey);
            var client = new OpenAI_API.OpenAIAPI(auth);
            var responseParams = new OpenAI_API.Chat.ChatRequest
            {
                Model = model,
                Messages = new[] { new OpenAI_API.Chat.ChatMessage { Role = ChatMessageRole.User, TextContent = prompt } },
                MaxTokens = maxTokens
            };
            var response = await client.Chat.CreateChatCompletionAsync(responseParams);
            var messageContent = response.Choices[0].Message.TextContent;
            PrintColored($"{model}:", color);
            PrintColored(messageContent, color);
            return messageContent;
        }
    }

    private static async Task<string> GetWebPageContentsAsync(string url)
    {
        using var client = new HttpClient();
        client.DefaultRequestHeaders.UserAgent.ParseAdd("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3");

        try
        {
            var response = await client.GetAsync(url);
            response.EnsureSuccessStatusCode();

            var htmlContent = await response.Content.ReadAsStringAsync();
            var htmlDocument = new HtmlDocument();
            htmlDocument.LoadHtml(htmlContent);

            return htmlDocument.DocumentNode.InnerText;
        }
        catch (HttpRequestException ex)
        {
            return ex.Message;
        }
    }

    private static void PlayMp3(string filePath)
    {
        using var audioFile = new AudioFileReader(filePath);
        using var outputDevice = new WaveOutEvent();
        outputDevice.Init(audioFile);
        outputDevice.Play();
        while (outputDevice.PlaybackState == PlaybackState.Playing)
        {
            System.Threading.Thread.Sleep(1000);
        }
    }

    private static string CleanAndShortenText(string text, int maxLength = 10)
    {
        var cleanText = new string(text.Where(char.IsLetterOrDigit).ToArray());
        return cleanText.Length > maxLength ? cleanText.Substring(0, maxLength) : cleanText;
    }

    private static string GenerateFilenameFromUrl(string url)
    {
        var uri = new Uri(url);
        var domainName = uri.Host.Split('.').Reverse().Skip(1).FirstOrDefault();
        var pathParts = uri.AbsolutePath.Split('/');
        var meaningfulParts = pathParts.Where(part => !string.IsNullOrEmpty(part)).Take(2).Select(CleanAndShortenText).ToArray();
        var filenameParts = new[] { CleanAndShortenText(domainName ?? "") }.Concat(meaningfulParts);
        var filename = string.Join("_", filenameParts);
        return $"{filename}.mp3";
    }

    private static int WordCount(string text)
    {
        return text.Split(new[] { ' ', '\t', '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries).Length;
    }

    private static async Task GenerateAudioAsync(string content, string voice, string filePath)
    {
        if (string.IsNullOrEmpty(voice))
            voice = "nova";

        var auth = new OpenAI_API.APIAuthentication(API_KEY);
        var client = new OpenAI_API.OpenAIAPI(auth);
        Console.WriteLine($"Generating Audio with {voice} Voice");

        var request = new TextToSpeechRequest()
        {
            Input = content,
            ResponseFormat = ResponseFormats.MP3,
            Model = Model.TTS_HD,
            Voice = Voices.Nova            
        };

        await client.TextToSpeech.SaveSpeechToFileAsync(request, filePath);
    }
}