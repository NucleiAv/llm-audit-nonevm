use anchor_lang::prelude::*;

declare_id!("BUMP1111111111111111111111111111111111111111");

#[program]
pub mod bump_vuln {
    use super::*;

    pub fn create_config(ctx: Context<CreateConfig>) -> Result<()> {
        let config = &mut ctx.accounts.config;
        config.bump = *ctx.bumps.get("config").unwrap();
        config.authority = ctx.accounts.payer.key();
        Ok(())
    }
}

#[derive(Accounts)]
pub struct CreateConfig<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + Config::SIZE,
        seeds = [b"config"],
        bump
    )]
    pub config: Account<'info, Config>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[account]
pub struct Config {
    pub bump: u8,
    pub authority: Pubkey,
}

impl Config {
    pub const SIZE: usize = 1 + 32;
}
