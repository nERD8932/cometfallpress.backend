create table if not exists newsletter_users (
    email text primary key not null,
    name text,
    datetime_joined timestamp default CURRENT_TIMESTAMP,
    unsubscribed integer not null default 0 check (unsubscribed in (0,1)),
    unsubscribe_secret text unique not null
);

create table if not exists newsletter_list (
    id integer primary key autoincrement,
    datetime_added timestamp default CURRENT_TIMESTAMP,
    email_content text not null,
    sent_to_users integer not null default 0,
    datetime_sent timestamp default null
);

create table if not exists newsletter_deliveries (
    id integer primary key autoincrement,
    newsletter_id integer not null,
    user_email text not null,
    datetime_sent timestamp default null,
    status text check (status in ('pending','sent','failed','opened')) default 'pending',

    foreign key (newsletter_id) references newsletter_list(id),
    foreign key (user_email) references newsletter_users(email),

    unique(newsletter_id, user_email)
);


